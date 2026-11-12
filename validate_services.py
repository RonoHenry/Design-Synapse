#!/usr/bin/env python3
"""
Validation script to check the current state of services
"""
import importlib
import sys
import traceback
from pathlib import Path


def validate_service_imports(service_name, service_path):
    """Validate that a service can be imported without errors"""
    print(f"\n=== Validating {service_name} ===")

    # Add service path to Python path
    sys.path.insert(0, str(service_path))

    try:
        # Try to import main modules
        if service_name == "user-service":
            from src.core.config import Settings
            from src.models.role import Role
            from src.models.user import User
            print("✅ User service imports successful")

        elif service_name == "knowledge-service":
            from knowledge_service.core.config import Settings
            from knowledge_service.models.resource import Resource
            print("✅ Knowledge service imports successful")

        elif service_name == "project-service":
            from src.models.project import Project
            from sin())ys.exit(ma":
    s"__main__name__ == f __
ireturn 1
     ")
   t issuesmpors have ie serviceom️  Sint("⚠      prse:
  eln 0
           returle!")
 rtabs are impoice"🎉 All servint(    prtal:
    tossed ==   if pa
  y")
    fullsuccessidated ces valserviotal} sed}/{terall: {pas"\nOv   print(f")

 status}20} {e:am"{nint(f      prL"
  else "❌ FAIt ulesif r"✅ PASS" = status
        lts.items():esu rult inor name, res
    f   (results)
  lenotal =  tult)
  s() if results.valuees result in rford = sum(1 passe
    "="*50)
int(   pr")
  SUMMARYVALIDATIONnt("50)
    pri" + "="*t("\n  prin
  yummar
    # S = False
 ce_name]lts[servi      resu
      ")e_path}st: {services not exiame} path do{service_nprint(f"❌          e:
         elsce_path)
  servirvice_name, ports(seservice_im = validate_ervice_name]ults[s res           exists():
path. if service_:
       vicesern svice_path ice_name, serrvir sefo

    ]
  ))-service"projectth("apps/Parvice", ct-se ("proje     ")),
  rviceedge-se/knowlpsPath("apice", ervge-sled   ("know")),
     rvices/user-sePath("appce", -servi  ("user
    = [   services service
 te each# Valida

    )n_packages(commoe_"] = validatnmo["com  resultsst
  ages fir common packalidate  # V
  ults = {}

    res
    ...")tureucfrastr InerviceValidating Sint("🔍
    pr"""ctionunn ftioin valida  """Ma:
   main()eflse

drn Fatu re
       print_exc()raceback.    t}")
    led: {et faiormpckages iommon pat(f"❌ C        prinas e:
xception     except E
ruereturn T
 sful")cesorts suc impagespackon mm("✅ Coprint    ngs
    Settit Base imporig.baseconf.common.kagespacm     fror
    idationError, Valport APIErrorors imerges.common.m packaro fy:
          tr)

 kages ==="mmon Pac Coingalidat= V== print("\n   """
importedbe ages can packon commlidate "Va ""():
   esmon_packagalidate_com
def vh))
_paticeservr(move(stys.path.re   s:
          in sys.pathce_path)ervir(sst
        if thmove from pa        # Re  finally:

  n False retur()
       .print_exc   traceback")
     ailed: {e}t fe} impornamvice_f"❌ {ser    print(s e:
    ption at Exceexcep
     rue
       urn T     ret

       ful")s successrtservice impo Project int("✅      prgs
      ettinfig import Sconrc.core.
