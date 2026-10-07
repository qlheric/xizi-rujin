from v2_08_lower_nonempty import normalize
assert normalize('ABC') == 'abc'
assert normalize('XyZ') == 'xyz'
