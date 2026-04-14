import re


def clean_name(name: str) -> str:
    # Replace spaces + remove special characters
    name = name.strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-zA-Z0-9_]", "", name)
    return name


def normalize_entity(name: str) -> str:
    return clean_name(name).upper()


def get_connector(cardinality: str) -> str:
    if cardinality == "1:N":
        return "||--o{"
    elif cardinality == "N:1":
        return "}o--||"
    elif cardinality == "1:1":
        return "||--||"
    else:
        return "--"


def get_label(rel) -> str:
    if getattr(rel, "label", None):
        return clean_name(rel.label).lower()

    desc = rel.description.lower()

    if "own" in desc:
        return "owns"
    if "transaction" in desc:
        return "records"
    if "account" in desc:
        return "has"

    # fallback
    return rel.to_entity.lower()


def build_mermaid(conceptual_model):
    lines = ["erDiagram"]

    # ✅ Entities
    for entity in conceptual_model.entities:
        entity_name = normalize_entity(entity.name)
        lines.append(f"  {entity_name} {{")

        for attr in entity.attributes:
            attr_name = clean_name(attr)
            lines.append(f"    string {attr_name}")

        lines.append("  }")

    # ✅ Relationships
    for rel in conceptual_model.relationships:
        from_entity = normalize_entity(rel.from_entity)
        to_entity = normalize_entity(rel.to_entity)

        connector = get_connector(rel.cardinality)
        label = get_label(rel)

        lines.append(
            f"  {from_entity} {connector} {to_entity} : {label}"
        )

    return "\n".join(lines)
