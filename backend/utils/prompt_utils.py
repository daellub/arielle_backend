# backend/utils/prompt_utils.py

def apply_variables(template: str, variables: list[str], values: dict[str, str]) -> str:
    """
    template 문자열에서 {변수} 형태를 실제 값으로 치환하는 함수.
    
    :param template: 원본 프롬프트 문자열
    :param variables: 사용할 변수 이름 목록 (예: ["time", "user_name"])
    :param values: 실제 치환할 값 딕셔너리 (예: {"time": "15:00", "user_name": "User"})
    :return: 치환된 문자열
    """
    result = template
    for var in variables:
        placeholder = f"{{{var}}}"
        value = values.get(var, f"{{{var}}}")
        result = result.replace(placeholder, value)
    return result