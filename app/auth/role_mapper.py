from typing import Iterable, List

from app.core.roles import Role


_CLAIM_TO_ROLE = {
    "admin": Role.SUPER_ADMIN,
    "application owners": Role.RP_ADMIN,
    "developer": Role.DEVELOPER,
}


def map_claims_to_roles(claims: Iterable[str]) -> List[Role]:
    mapped: List[Role] = []
    for claim in claims:
        try:
            mapped.append(Role(claim))
            continue
        except ValueError:
            alias = _CLAIM_TO_ROLE.get(str(claim).lower())
            if alias:
                mapped.append(alias)
    return mapped
