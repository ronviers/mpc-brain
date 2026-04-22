"""metareasoner pack unit test — runs AMEND-008 acceptance test.

Invocation:
    PYTHONPATH=/mnt/user-data/uploads:/mnt/user-data/outputs/session5a \
      python -m mpc_packs.metareasoner.test_pack
"""

from mpc_packs.metareasoner.pack import test_amend008


def main() -> int:
    ok = test_amend008()
    print(f"AMEND-008 test_amend008: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
