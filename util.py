def query_add_md(q: str):
    if not q.endswith('.') or not q.endswith('?'):
        q = q + '.'
    return q + "save the result in a json format, the keys are result, your confidence level(high/middle/low), and evidence."


def convert_string_to_num(s):
    raw = str(s)
    if raw.isdigit():
        return int(raw)
    try:
        f = float(s)
        return f
    except ValueError:
        pass
    return str(s)

if __name__ == '__main__':
    result = convert_string_to_num('1,377')
    print(type(result))