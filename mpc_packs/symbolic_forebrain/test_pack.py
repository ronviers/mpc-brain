"""symbolic_forebrain pack unit test — runs AMEND-009 Test A and Test B.

Invocation:
    PYTHONPATH=/mnt/user-data/uploads:/mnt/user-data/outputs/session5a \
      python -m mpc_packs.symbolic_forebrain.test_pack
"""

from mpc_packs.symbolic_forebrain.pack import test_amend009


def main() -> int:
    a, b = test_amend009()
    print(f"AMEND-009A test_amend009 predicates: {'PASS' if a else 'FAIL'}")
    print(f"AMEND-009B test_amend009 execute:    {'PASS' if b else 'FAIL'}")
    return 0 if (a and b) else 1


if __name__ == "__main__":
    raise SystemExit(main())
