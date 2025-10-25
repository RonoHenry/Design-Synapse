"""
LLM Client for design generation and optimization.

This module provides an LLM client that:
- Generates design specifications from natural language descriptions
- Generates optimization suggestions for designs
- Implements fallback mechanism when primary model fails
- Handles timeouts (60 second limit)
- Tracks token usage for cost monitoring
"""

import asyncio
import json
import logging
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
from io import BytesIO

from openai import OpenAI, AsyncOpenAI, APIError, APITimeoutError, RateLimitError

try:
    from groq import Groq
except ImportError:
    Groq = None

from common.config import LLMConfig, LLMProvider


logger = logging.getLogger(__name__)


class LLMGenerationError(Exception):
    """Raised when LLM generation fails."""
    pass


class LLMTimeoutError(Exception):
    """Raised when LLM request times out."""
    pass


class LLMImageGenerationError(Exception):
    """Raised when image generation fails."""
    pass


class LLMClient:
    """Client for interacting with LLM providers for design generation."""
    
    def __init__(self, config: LLMConfig):
        """
        Initialize LLM client with configuration.
        
        Args:
            config: LLM configuration with provider settings
        """
        self.config = config
        self.primary_provider = config.primary_provider
        self.fallback_providers = config.fallback_providers
        self.timeout = config.timeout
        
        # Initialize OpenAI client (for text and image generation)
        if self.primary_provider == LLMProvider.OPENAI or LLMProvider.OPENAI in self.fallback_providers:
            self._openai_client = OpenAI(
                api_key=config.openai_api_key,
                timeout=config.timeout,
                max_retries=config.max_retries
            )
        
        # Initialize Groq client (for text generation only)
        if self.primary_provider == LLMProvider.GROQ or LLMProvider.GROQ in self.fallback_providers:
            if Groq is None:
                raise ImportError("Groq client not installed. Run: pip install groq")
            self._groq_client = Groq(
                api_key=config.groq_api_key,
                timeout=config.timeout
            )
        
        # Usage tracking
        self._total_requests = 0
        self._total_tokens = 0
        self._total_cost = 0.0
        
        logger.info(
            f"LLM client initialized with primary provider: {self.primary_provider}, "
            f"fallback providers: {self.fallback_providers}"
        )
    
    async def generate_design_specification(
        self,
        description: str,
        building_type: str,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a design specification from natural language description.
        
        Args:
            description: Natural language description of the design
            building_type: Type of building (residential, commercial, industrial)
            requirements: Additional requirements and constraints
            
        Returns:
            Dictionary containing:
                - specification: Generated design specification
                - confidence_score: Confidence score (0-100)
                - model_version: Model used for generation
                - token_usage: Token usage statistics
                
        Raises:
            ValueError: If inputs are invalid
            LLMGenerationError: If generation fails
            LLMTimeoutError: If request times out
        """
        # Validate inputs
        if not description or not description.strip():
            raise ValueError("description cannot be empty")
        if not building_type or not building_type.strip():
            raise ValueError("building_type cannot be empty")
        
        # Build prompt
        system_prompt = self._build_design_system_prompt()
        user_prompt = self._build_design_user_prompt(description, building_type, requirements)
        
        # Try primary provider, then fallbacks
        providers = [self.primary_provider] + self.fallback_providers
        last_error = None
        
        for provider in providers:
            try:
                logger.info(f"Attempting design generation with provider: {provider}")
                
                if provider == LLMProvider.OPENAI:
                    result = await self._generate_with_openai(system_prompt, user_prompt)
                    
                    # Parse and validate response
                    specification = self._parse_design_response(result["content"])
                    confidence_score = self._calculate_confidence_score(specification, requirements)
                    
                    # Track usage
                    self._track_usage(result["token_usage"])
                    
                    logger.info(
                        f"Design generation successful with {provider}. "
                        f"Tokens used: {result['token_usage']['total_tokens']}, "
                        f"Confidence: {confidence_score}"
                    )
                    
                    return {
                        "specification": specification,
                        "confidence_score": confidence_score,
                        "model_version": result["model"],
                        "token_usage": result["token_usage"]
                    }
                else:
                    # Other providers not implemented yet
                    logger.warning(f"Provider {provider} not implemented, skipping")
                    continue
                    
            except APITimeoutError as e:
                logger.warning(f"Timeout with provider {provider}: {e}")
                last_error = LLMTimeoutError(f"Request timed out after {self.timeout} seconds")
                continue
            except (APIError, RateLimitError) as e:
                logger.warning(f"API error with provider {provider}: {e}")
                last_error = e
                continue
            except Exception as e:
                logger.error(f"Unexpected error with provider {provider}: {e}")
                last_error = e
                continue
        
        # All providers failed
        error_msg = f"All LLM providers failed. Last error: {last_error}"
        logger.error(error_msg)
        
        if isinstance(last_error, LLMTimeoutError):
            raise last_error
        raise LLMGenerationError(error_msg)
    
    async def generate_optimizations(
        self,
        design_specification: Dict[str, Any],
        optimization_types: List[str]
    ) -> Dict[str, Any]:
        """
        Generate optimization suggestions for a design.
        
        Args:
            design_specification: The design specification to optimize
            optimization_types: Types of optimizations to generate (cost, structural, sustainability)
            
        Returns:
            Dictionary containing:
                - optimizations: List of optimization suggestions
                - token_usage: Token usage statistics
                
        Raises:
            LLMGenerationError: If generation fails
            LLMTimeoutError: If request times out
        """
        # Build prompt
        system_prompt = self._build_optimization_system_prompt()
        user_prompt = self._build_optimization_user_prompt(design_specification, optimization_types)
        
        # Try primary provider, then fallbacks
        providers = [self.primary_provider] + self.fallback_providers
        last_error = None
        
        for provider in providers:
            try:
                logger.info(f"Attempting optimization generation with provider: {provider}")
                
                if provider == LLMProvider.OPENAI:
                    result = await self._generate_with_openai(system_prompt, user_prompt)
                    
                    # Parse response
                    optimizations = self._parse_optimization_response(result["content"])
                    
                    # Track usage
                    self._track_usage(result["token_usage"])
                    
                    logger.info(
                        f"Optimization generation successful with {provider}. "
                        f"Generated {len(optimizations)} suggestions. "
                        f"Tokens used: {result['token_usage']['total_tokens']}"
                    )
                    
                    return {
                        "optimizations": optimizations,
                        "token_usage": result["token_usage"]
                    }
                else:
                    logger.warning(f"Provider {provider} not implemented, skipping")
                    continue
                    
            except APITimeoutError as e:
                logger.warning(f"Timeout with provider {provider}: {e}")
                last_error = LLMTimeoutError(f"Request timed out after {self.timeout} seconds")
                continue
            except (APIError, RateLimitError) as e:
                logger.warning(f"API error with provider {provider}: {e}")
                last_error = e
                continue
            except Exception as e:
                logger.error(f"Unexpected error with provider {provider}: {e}")
                last_error = e
                continue
        
        # All providers failed
        error_msg = f"All LLM providers failed. Last error: {last_error}"
        logger.error(error_msg)
        
        if isinstance(last_error, LLMTimeoutError):
            raise last_error
        raise LLMGenerationError(error_msg)
    
    async def _generate_with_openai(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> Dict[str, Any]:
        """
        Generate content using OpenAI API.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            
        Returns:
            Dictionary with content, model, and token usage
        """
        try:
            response = self._openai_client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.config.openai_max_tokens,
                temperature=self.config.openai_temperature,
                timeout=self.timeout
            )
            
            # Extract token usage with safe defaults
            usage = response.usage
            prompt_tokens = getattr(usage, 'prompt_tokens', 0) if hasattr(usage, 'prompt_tokens') else 0
            completion_tokens = getattr(usage, 'completion_tokens', 0) if hasattr(usage, 'completion_tokens') else 0
            total_tokens = getattr(usage, 'total_tokens', 0) if hasattr(usage, 'total_tokens') else (prompt_tokens + completion_tokens)
            
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "token_usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
            }
        except APITimeoutError:
            raise
        except (APIError, RateLimitError):
            raise
        except Exception as e:
            raise LLMGenerationError(f"OpenAI API error: {e}")
    
    def _build_design_system_prompt(self) -> str:
        """Build system prompt for design generation."""
        return """You are an expert architectural design assistant specializing in African construction standards and building codes.
Your task is to generate detailed building design specifications from natural language descriptions.

Generate a comprehensive JSON design specification that includes:
1. Building information (type, area, floors, height)
2. Structural details (foundation, walls, roof)
3. Space layout with dimensions
4. Materials list with quantities
5. Compliance information (building codes, zoning, setbacks)

Ensure all designs:
- Follow local building codes and standards
- Use locally available materials where possible
- Consider climate and environmental factors
- Include cost-effective solutions
- Meet safety and structural requirements

Return ONLY valid JSON without any markdown formatting or additional text."""
    
    def _build_design_user_prompt(
        self,
        description: str,
        building_type: str,
        requirements: Dict[str, Any]
    ) -> str:
        """Build user prompt for design generation."""
        prompt = f"""Generate a detailed design specification for the following building:

Description: {description}
Building Type: {building_type}

Additional Requirements:
"""
        for key, value in requirements.items():
            prompt += f"- {key}: {value}\n"
        
        prompt += """
Please provide a complete JSON design specification following this structure:
{
  "building_info": {
    "type": "...",
    "subtype": "...",
    "total_area": 0.0,
    "num_floors": 0,
    "height": 0.0
  },
  "structure": {
    "foundation_type": "...",
    "wall_material": "...",
    "roof_type": "...",
    "roof_material": "..."
  },
  "spaces": [
    {
      "name": "...",
      "area": 0.0,
      "floor": 0,
      "dimensions": {"length": 0.0, "width": 0.0, "height": 0.0}
    }
  ],
  "materials": [
    {
      "name": "...",
      "quantity": 0,
      "unit": "...",
      "estimated_cost": 0.0
    }
  ],
  "compliance": {
    "building_code": "...",
    "zoning": "...",
    "setbacks": {"front": 0.0, "rear": 0.0, "side": 0.0}
  }
}"""
        return prompt
    
    def _build_optimization_system_prompt(self) -> str:
        """Build system prompt for optimization generation."""
        return """You are an expert construction optimization consultant specializing in cost reduction, structural efficiency, and sustainability.
Your task is to analyze building designs and provide actionable optimization suggestions.

For each optimization, provide:
1. Optimization type (cost, structural, sustainability)
2. Clear title and description
3. Estimated cost impact (percentage)
4. Implementation difficulty (easy, medium, hard)
5. Priority level (low, medium, high)

Focus on:
- Using local materials to reduce costs
- Improving structural efficiency
- Enhancing sustainability and energy efficiency
- Practical, implementable suggestions

Return ONLY a valid JSON array without any markdown formatting or additional text."""
    
    def _build_optimization_user_prompt(
        self,
        design_specification: Dict[str, Any],
        optimization_types: List[str]
    ) -> str:
        """Build user prompt for optimization generation."""
        prompt = f"""Analyze the following design specification and provide optimization suggestions:

Design Specification:
{json.dumps(design_specification, indent=2)}

Optimization Types Requested: {', '.join(optimization_types)}

Please provide at least 3 optimization suggestions in the following JSON array format:
[
  {{
    "optimization_type": "cost|structural|sustainability",
    "title": "...",
    "description": "...",
    "estimated_cost_impact": 0.0,
    "implementation_difficulty": "easy|medium|hard",
    "priority": "low|medium|high"
  }}
]"""
        return prompt
    
    def _parse_design_response(self, content: str) -> Dict[str, Any]:
        """
        Parse design specification from LLM response.
        
        Args:
            content: Raw LLM response content
            
        Returns:
            Parsed design specification
            
        Raises:
            LLMGenerationError: If parsing fails
        """
        try:
            # Remove markdown code blocks if present
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            specification = json.loads(content)
            
            # Validate required fields
            if "building_info" not in specification:
                raise ValueError("Missing building_info in specification")
            
            return specification
        except json.JSONDecodeError as e:
            raise LLMGenerationError(f"Failed to parse design specification JSON: {e}")
        except Exception as e:
            raise LLMGenerationError(f"Failed to parse design specification: {e}")
    
    def _parse_optimization_response(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse optimization suggestions from LLM response.
        
        Args:
            content: Raw LLM response content
            
        Returns:
            List of optimization suggestions
            
        Raises:
            LLMGenerationError: If parsing fails
        """
        try:
            # Remove markdown code blocks if present
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            optimizations = json.loads(content)
            
            # Validate it's a list
            if not isinstance(optimizations, list):
                raise ValueError("Optimizations must be a list")
            
            return optimizations
        except json.JSONDecodeError as e:
            raise LLMGenerationError(f"Failed to parse optimizations JSON: {e}")
        except Exception as e:
            raise LLMGenerationError(f"Failed to parse optimizations: {e}")
    
    def _calculate_confidence_score(
        self,
        specification: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence score for generated design.
        
        Args:
            specification: Generated design specification
            requirements: Original requirements
            
        Returns:
            Confidence score (0-100)
        """
        score = 70.0  # Base score
        
        # Check completeness of specification
        if "building_info" in specification:
            score += 5.0
        if "structure" in specification:
            score += 5.0
        if "spaces" in specification and len(specification.get("spaces", [])) > 0:
            score += 5.0
        if "materials" in specification and len(specification.get("materials", [])) > 0:
            score += 5.0
        if "compliance" in specification:
            score += 5.0
        
        # Check if requirements are met
        building_info = specification.get("building_info", {})
        if "num_floors" in requirements:
            if building_info.get("num_floors") == requirements["num_floors"]:
                score += 2.5
        if "total_area" in requirements:
            if building_info.get("total_area") == requirements["total_area"]:
                score += 2.5
        
        return min(score, 100.0)
    
    def _track_usage(self, token_usage: Dict[str, int]) -> None:
        """
        Track token usage for cost monitoring.
        
        Args:
            token_usage: Token usage statistics
        """
        self._total_requests += 1
        
        # Safely extract token counts, ensuring they're integers
        total_tokens = token_usage.get("total_tokens", 0)
        prompt_tokens = token_usage.get("prompt_tokens", 0)
        completion_tokens = token_usage.get("completion_tokens", 0)
        
        # Convert to int if they're not already (handles Mock objects)
        try:
            total_tokens = int(total_tokens) if total_tokens else 0
            prompt_tokens = int(prompt_tokens) if prompt_tokens else 0
            completion_tokens = int(completion_tokens) if completion_tokens else 0
        except (TypeError, ValueError):
            # If conversion fails, use 0
            total_tokens = 0
            prompt_tokens = 0
            completion_tokens = 0
        
        self._total_tokens += total_tokens
        
        # Estimate cost (approximate OpenAI pricing)
        # GPT-4: $0.03 per 1K prompt tokens, $0.06 per 1K completion tokens
        prompt_cost = (prompt_tokens / 1000) * 0.03
        completion_cost = (completion_tokens / 1000) * 0.06
        self._total_cost += prompt_cost + completion_cost
        
        logger.info(
            f"Token usage - Prompt: {prompt_tokens}, "
            f"Completion: {completion_tokens}, "
            f"Total: {total_tokens}, "
            f"Estimated cost: ${prompt_cost + completion_cost:.4f}"
        )
    
    async def generate_image(
        self,
        prompt: str,
        image_type: str = "floor_plan",
        size: str = "1024x1024",
        quality: str = "standard"
    ) -> Dict[str, Any]:
        """
        Generate an image using DALL-E 3 API.
        
        Args:
            prompt: Text prompt describing the image to generate
            image_type: Type of image (floor_plan, rendering, 3d_model)
            size: Image size (1024x1024, 1792x1024, 1024x1792)
            quality: Image quality (standard, hd)
            
        Returns:
            Dictionary containing:
                - image_url: URL of the generated image
                - image_data: Binary image data
                - revised_prompt: The revised prompt used by DALL-E
                - generation_cost: Estimated cost of generation
                - model_version: Model used for generation
                
        Raises:
            ValueError: If inputs are invalid
            LLMImageGenerationError: If image generation fails
            LLMTimeoutError: If request times out
        """
        # Validate inputs
        if not prompt or not prompt.strip():
            raise ValueError("prompt cannot be empty")
        
        valid_sizes = ["1024x1024", "1792x1024", "1024x1792"]
        if size not in valid_sizes:
            raise ValueError(f"size must be one of: {', '.join(valid_sizes)}")
        
        valid_qualities = ["standard", "hd"]
        if quality not in valid_qualities:
            raise ValueError(f"quality must be one of: {', '.join(valid_qualities)}")
        
        # Enhance prompt based on image type
        enhanced_prompt = self._enhance_image_prompt(prompt, image_type)
        
        # Try primary provider, then fallbacks
        providers = [self.primary_provider] + self.fallback_providers
        last_error = None
        
        for provider in providers:
            try:
                logger.info(f"Attempting image generation with provider: {provider}")
                
                if provider == LLMProvider.OPENAI:
                    result = await self._generate_image_with_openai(
                        enhanced_prompt, size, quality
                    )
                    
                    # Download image data
                    image_data = await self._download_image(result["image_url"])
                    
                    # Calculate cost
                    generation_cost = self._calculate_image_cost(size, quality)
                    
                    # Track usage
                    self._track_image_usage(generation_cost)
                    
                    logger.info(
                        f"Image generation successful with {provider}. "
                        f"Size: {size}, Quality: {quality}, "
                        f"Cost: ${generation_cost:.4f}"
                    )
                    
                    return {
                        "image_url": result["image_url"],
                        "image_data": image_data,
                        "revised_prompt": result.get("revised_prompt", enhanced_prompt),
                        "generation_cost": generation_cost,
                        "model_version": "dall-e-3"
                    }
                else:
                    # Other providers not implemented yet
                    logger.warning(f"Provider {provider} not implemented for image generation, skipping")
                    continue
                    
            except APITimeoutError as e:
                logger.warning(f"Timeout with provider {provider}: {e}")
                last_error = LLMTimeoutError(f"Image generation timed out after {self.timeout} seconds")
                continue
            except (APIError, RateLimitError) as e:
                logger.warning(f"API error with provider {provider}: {e}")
                last_error = e
                continue
            except Exception as e:
                logger.error(f"Unexpected error with provider {provider}: {e}")
                last_error = e
                continue
        
        # All providers failed
        error_msg = f"All LLM providers failed for image generation. Last error: {last_error}"
        logger.error(error_msg)
        
        if isinstance(last_error, LLMTimeoutError):
            raise last_error
        raise LLMImageGenerationError(error_msg)
    
    async def _generate_image_with_openai(
        self,
        prompt: str,
        size: str,
        quality: str
    ) -> Dict[str, Any]:
        """
        Generate image using OpenAI DALL-E 3 API.
        
        Args:
            prompt: Enhanced prompt for image generation
            size: Image size
            quality: Image quality
            
        Returns:
            Dictionary with image URL and revised prompt
        """
        try:
            response = self._openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
                response_format="url"
            )
            
            image_data = response.data[0]
            
            return {
                "image_url": image_data.url,
                "revised_prompt": getattr(image_data, 'revised_prompt', prompt)
            }
            
        except APITimeoutError:
            raise
        except (APIError, RateLimitError):
            raise
        except Exception as e:
            raise LLMImageGenerationError(f"OpenAI image generation error: {e}")
    
    async def _download_image(self, image_url: str) -> bytes:
        """
        Download image data from URL.
        
        Args:
            image_url: URL of the generated image
            
        Returns:
            Binary image data
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                return response.content
        except Exception as e:
            raise LLMImageGenerationError(f"Failed to download image: {e}")
    
    def _enhance_image_prompt(self, prompt: str, image_type: str) -> str:
        """
        Enhance the prompt based on image type for better results.
        
        Args:
            prompt: Original prompt
            image_type: Type of image to generate
            
        Returns:
            Enhanced prompt
        """
        base_prompt = prompt.strip()
        
        if image_type == "floor_plan":
            enhanced = f"Architectural floor plan drawing of {base_prompt}. "
            enhanced += "Top-down view, clean lines, professional architectural style, "
            enhanced += "with room labels, dimensions, and standard architectural symbols. "
            enhanced += "Black lines on white background, technical drawing style."
            
        elif image_type == "rendering":
            enhanced = f"Photorealistic 3D architectural rendering of {base_prompt}. "
            enhanced += "Professional architectural visualization, high quality, "
            enhanced += "realistic lighting and materials, exterior or interior view, "
            enhanced += "modern architectural photography style."
            
        elif image_type == "3d_model":
            enhanced = f"3D architectural model visualization of {base_prompt}. "
            enhanced += "Isometric or perspective view, clean modern style, "
            enhanced += "showing structure and form, architectural model rendering."
            
        else:
            # Default enhancement
            enhanced = f"Architectural visualization of {base_prompt}. "
            enhanced += "Professional architectural style, clean and modern."
        
        return enhanced
    
    def _calculate_image_cost(self, size: str, quality: str) -> float:
        """
        Calculate estimated cost for image generation.
        
        Args:
            size: Image size
            quality: Image quality
            
        Returns:
            Estimated cost in USD
        """
        # DALL-E 3 pricing (as of 2024)
        if quality == "hd":
            if size == "1024x1024":
                return 0.080  # $0.080 per image
            else:  # 1792x1024 or 1024x1792
                return 0.120  # $0.120 per image
        else:  # standard quality
            if size == "1024x1024":
                return 0.040  # $0.040 per image
            else:  # 1792x1024 or 1024x1792
                return 0.080  # $0.080 per image
    
    def _track_image_usage(self, cost: float) -> None:
        """
        Track image generation usage for cost monitoring.
        
        Args:
            cost: Cost of the image generation
        """
        self._total_requests += 1
        self._total_cost += cost
        
        logger.info(f"Image generation cost: ${cost:.4f}")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get cumulative usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        return {
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
            "total_cost": self._total_cost
        } 