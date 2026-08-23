"""
akaalEngine.schema.procedural.transforms.packages
=================================================
Package decomposition and namespace routing for Oracle packages.
Translates Oracle package structures into schema-namespaced routines.
"""

from __future__ import annotations

from typing import List, Tuple

from akaalEngine.schema.procedural.ast_nodes import PackageAST, RoutineAST


class PackageTransformer:
    """Decomposes Oracle packages into standalone functions/procedures prefixed or namespaced."""

    @classmethod
    def decompose_package(cls, pkg: PackageAST, target_schema: str = "public") -> List[RoutineAST]:
        decomposed: List[RoutineAST] = []
        pkg_prefix = pkg.name.lower()

        # Combine spec and body routines
        routines = list(pkg.body_routines) if pkg.body_routines else list(pkg.spec_routines)
        for r in routines:
            # Prefix routine name with package name (e.g. pkg_order_process_order)
            new_name = f"{pkg_prefix}_{r.name}"
            decomposed.append(
                RoutineAST(
                    name=new_name,
                    routine_type=r.routine_type,
                    parameters=r.parameters,
                    return_type=r.return_type,
                    body=r.body,
                    is_autonomous=r.is_autonomous,
                    extra={"original_package": pkg.name},
                )
            )
        return decomposed
