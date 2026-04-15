import re


def clean_name(name: str) -> str:
    if not name:
        return "UNKNOWN"

    name = name.strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-zA-Z0-9_]", "", name)

    return name or "UNKNOWN"


def normalize_entity(name: str) -> str:
    return clean_name(name).upper()



def get_connector(cardinality: str) -> str:
    if not cardinality:
        return "||--o{"

    cardinality = cardinality.replace(" ", "").upper()

    if cardinality in ["1:N", "1-M", "ONE_TO_MANY"]:
        return "||--o{"
    elif cardinality in ["N:1", "M-1", "MANY_TO_ONE"]:
        return "}o--||"
    elif cardinality in ["1:1", "ONE_TO_ONE"]:
        return "||--||"
    elif cardinality in ["M:N", "N:N", "M-M", "MANY_TO_MANY"]:
        return "}o--o{"


    return "||--o{"


def get_label(rel) -> str:
    if getattr(rel, "label", None):
        return clean_name(rel.label).lower()

    desc = getattr(rel, "description", "") or ""
    desc = desc.lower()

    if "own" in desc:
        return "owns"
    if "transaction" in desc:
        return "records"
    if "account" in desc:
        return "has"


    return clean_name(rel.to_entity).lower()


def build_mermaid(conceptual_model):
    lines = ["erDiagram"]

    
    for entity in conceptual_model.entities:
        entity_name = normalize_entity(entity.name)
        lines.append(f"  {entity_name} {{")

        for attr in entity.attributes:
            attr_name = clean_name(attr)
            lines.append(f"    string {attr_name}")

        lines.append("  }")

    
    for rel in conceptual_model.relationships:
        from_entity = normalize_entity(rel.from_entity)
        to_entity = normalize_entity(rel.to_entity)

        connector = get_connector(getattr(rel, "cardinality", ""))
        label = get_label(rel)

        lines.append(
            f"  {from_entity} {connector} {to_entity} : {label}"
        )

    return "\n".join(lines)