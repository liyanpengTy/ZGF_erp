"""RESTX 命名空间注册工具。"""

from typing import Iterable, List, Sequence, Tuple


NamespaceRoute = Tuple[object, str]


def build_namespace_routes(*routes: NamespaceRoute) -> List[NamespaceRoute]:
    """构建并校验单模块命名空间路由列表。"""
    validate_namespace_routes(routes)
    return list(routes)


def merge_namespace_routes(*groups: Sequence[NamespaceRoute]) -> List[NamespaceRoute]:
    """合并并校验多组命名空间路由。"""
    merged: List[NamespaceRoute] = []
    for group in groups:
        merged.extend(group)
    validate_namespace_routes(merged)
    return merged


def validate_namespace_routes(routes: Iterable[NamespaceRoute]):
    """校验命名空间名称与挂载路径是否重复。"""
    seen_names = {}
    seen_paths = {}

    for namespace, path in routes:
        namespace_name = getattr(namespace, 'name', None)
        if not namespace_name:
            raise ValueError(f'命名空间缺少 name: {namespace}')
        if not path or not isinstance(path, str):
            raise ValueError(f'命名空间 {namespace_name} 缺少有效 path')

        existing_name_path = seen_names.get(namespace_name)
        if existing_name_path and existing_name_path != path:
            raise ValueError(f'命名空间名称重复且路径不一致: {namespace_name} -> {existing_name_path}, {path}')
        seen_names[namespace_name] = path

        existing_path_name = seen_paths.get(path)
        if existing_path_name and existing_path_name != namespace_name:
            raise ValueError(f'命名空间路径重复: {path} -> {existing_path_name}, {namespace_name}')
        seen_paths[path] = namespace_name


def register_namespace_routes(api, routes: Sequence[NamespaceRoute]):
    """按顺序注册命名空间列表。"""
    validate_namespace_routes(routes)
    for namespace, path in routes:
        api.add_namespace(namespace, path=path)
