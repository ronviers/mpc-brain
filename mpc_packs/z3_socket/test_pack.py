"""z3_socket pack unit test — runs AMEND-007 acceptance test.

Invocation:
    PYTHONPATH=/mnt/user-data/uploads:/mnt/user-data/outputs/session5a \
      python -m mpc_packs.z3_socket.test_pack
"""

from mpc_packs.z3_socket.pack import test_amend007


def main() -> int:
    ok = test_amend007()
    print(f"AMEND-007 test_amend007: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
