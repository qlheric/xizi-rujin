from trap_05_except_pass import parse_int
def test_it():
    try:
        parse_int('abc')
    except Exception:
        pass
