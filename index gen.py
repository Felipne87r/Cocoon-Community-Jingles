import os
import json
import re


ROOT_DIR = "jingles"
COLLECTION_NAME = "Cocoon Community Jingles"
ALIASES_FILE = "aliases.json"

AUDIO_EXTENSIONS = {
    ".ogg",
    ".mp3",
    ".wav",
    ".flac",
    ".m4a"
}


ROMAN_NUMERALS = {
    "i": "1",
    "ii": "2",
    "iii": "3",
    "iv": "4",
    "v": "5",
    "vi": "6",
    "vii": "7",
    "viii": "8",
    "ix": "9",
    "x": "10",
    "xi": "11",
    "xii": "12",
    "xiii": "13",
    "xiv": "14",
    "xv": "15",
    "xvi": "16",
    "xvii": "17",
    "xviii": "18",
    "xix": "19",
    "xx": "20"
}

ARABIC_TO_ROMAN = {
    arabic: roman
    for roman, arabic in ROMAN_NUMERALS.items()
}


def load_aliases():
    if not os.path.exists(ALIASES_FILE):
        return {}

    try:
        with open(ALIASES_FILE, "r", encoding="utf-8") as f:
            aliases = json.load(f)

    except json.JSONDecodeError as e:
        print(f"Warning: Could not parse {ALIASES_FILE}: {e}")
        return {}

    if not isinstance(aliases, dict):
        print(f"Warning: {ALIASES_FILE} must contain a JSON object.")
        return {}

    return aliases


def make_alias_key(title):
    parts = re.findall(
        r"[a-zA-Z0-9]+",
        title.lower()
    )

    normalised = []

    for part in parts:

        if part in ROMAN_NUMERALS:
            normalised.append(
                ROMAN_NUMERALS[part]
            )

        else:
            normalised.append(part)

    return " ".join(normalised)


def build_alias_lookup(alias_data):
    lookup = {}

    for canonical, aliases in alias_data.items():

        if not isinstance(canonical, str):
            continue

        if not isinstance(aliases, list):
            continue

        canonical = canonical.strip()

        if not canonical:
            continue

        group = [canonical]

        for alias in aliases:

            if not isinstance(alias, str):
                continue

            alias = alias.strip()

            if not alias:
                continue

            if alias.lower() == canonical.lower():
                continue

            group.append(alias)

        for name in group:

            key = make_alias_key(name)

            lookup[key] = [
                other
                for other in group
                if other.lower() != name.lower()
            ]

    return lookup


def extract_title_and_brackets(filename):
    name = os.path.splitext(filename)[0]
    brackets = []

    while True:

        match = re.search(
            r"\s*\(([^()]*)\)\s*$",
            name
        )

        if not match:
            break

        bracket_text = match.group(1).strip()

        if bracket_text:
            brackets.insert(0, bracket_text)

        name = name[:match.start()].strip()

    return name, brackets


def normalise_text(text):
    return re.findall(
        r"[a-zA-Z0-9]+",
        text.lower()
    )


def make_token_pattern(token):
    token = token.lower()

    if token in ROMAN_NUMERALS:

        arabic = ROMAN_NUMERALS[token]

        return (
            "(?:"
            + re.escape(token)
            + "|"
            + re.escape(arabic)
            + ")"
        )

    if token in ARABIC_TO_ROMAN:

        roman = ARABIC_TO_ROMAN[token]

        return (
            "(?:"
            + re.escape(token)
            + "|"
            + re.escape(roman)
            + ")"
        )

    return re.escape(token)


def make_title_pattern(title):
    parts = normalise_text(title)

    if not parts:
        return None

    separator = r"[^a-z0-9]+"

    return separator.join(
        make_token_pattern(part)
        for part in parts
    )


def make_title_patterns(title):
    patterns = []

    full_pattern = make_title_pattern(title)

    if full_pattern:
        patterns.append(
            full_pattern
        )

    hyphen_match = re.search(
        r"\s+-\s+",
        title
    )

    if hyphen_match:

        main_title = title[
            :hyphen_match.start()
        ].strip()

        subtitle = title[
            hyphen_match.end():
        ].strip()

        main_pattern = make_title_pattern(
            main_title
        )

        subtitle_pattern = make_title_pattern(
            subtitle
        )

        if main_pattern and subtitle_pattern:

            patterns.append(
                main_pattern
            )

            patterns.append(
                main_pattern
                + r"[^a-z0-9]+"
                + subtitle_pattern
            )

    return list(
        dict.fromkeys(patterns)
    )


def make_regex(
    title,
    platform,
    bracket_extras=None,
    aliases=None
):
    bracket_extras = bracket_extras or []
    aliases = aliases or []

    search_titles = [title]

    for alias in aliases:

        if alias.lower() == title.lower():
            continue

        if not any(
            alias.lower() == existing.lower()
            for existing in search_titles
        ):
            search_titles.append(alias)

    title_patterns = []

    for search_title in search_titles:

        title_patterns.extend(
            make_title_patterns(
                search_title
            )
        )

    title_patterns = list(
        dict.fromkeys(
            title_patterns
        )
    )

    patterns = list(title_patterns)

    for bracket in bracket_extras:

        bracket_pattern = make_title_pattern(
            bracket
        )

        if not bracket_pattern:
            continue

        for title_pattern in title_patterns:

            patterns.append(
                title_pattern
                + r"[^a-z0-9]+"
                + bracket_pattern
            )

    platform_pattern = make_title_pattern(
        platform
    )

    if platform_pattern:

        base_patterns = list(patterns)

        for pattern in base_patterns:

            patterns.append(
                platform_pattern
                + r"[^a-z0-9]+"
                + pattern
            )

    final_patterns = []

    for pattern in patterns:

        final_patterns.append(
            pattern + "$"
        )

    final_patterns = list(
        dict.fromkeys(
            final_patterns
        )
    )

    if not final_patterns:
        return "^$"

    if len(final_patterns) == 1:
        return final_patterns[0]

    return (
        "(?:"
        + "|".join(final_patterns)
        + ")"
    )


ALIAS_DATA = load_aliases()
ALIAS_LOOKUP = build_alias_lookup(ALIAS_DATA)

data = {
    "name": COLLECTION_NAME
}


if not os.path.isdir(ROOT_DIR):
    raise FileNotFoundError(
        f"Could not find jingles directory: {ROOT_DIR}"
    )


for platform in sorted(
    os.listdir(ROOT_DIR),
    key=str.lower
):

    platform_path = os.path.join(
        ROOT_DIR,
        platform
    )

    if not os.path.isdir(platform_path):
        continue

    entries = []

    for root, _, files in os.walk(platform_path):

        for file in sorted(
            files,
            key=str.lower
        ):

            extension = os.path.splitext(
                file
            )[1].lower()

            if extension not in AUDIO_EXTENSIONS:
                continue

            full_path = os.path.join(
                root,
                file
            )

            relative_to_jingles = os.path.relpath(
                full_path,
                ROOT_DIR
            )

            path_parts = relative_to_jingles.split(
                os.sep
            )

            if len(path_parts) < 3:

                print(
                    "Warning: Skipping unexpected path:",
                    full_path
                )

                continue

            detected_platform = path_parts[0]

            display_name, bracket_extras = (
                extract_title_and_brackets(file)
            )

            alias_key = make_alias_key(
                display_name
            )

            aliases = ALIAS_LOOKUP.get(
                alias_key,
                []
            )

            regex = make_regex(
                display_name,
                detected_platform,
                bracket_extras,
                aliases
            )

            relative_path = os.path.relpath(
                full_path,
                "."
            ).replace(
                "\\",
                "/"
            )

            entries.append({
                "game": display_name,
                "file": relative_path,
                "regex": regex
            })

    data[platform] = sorted(
        entries,
        key=lambda x: x["game"].lower()
    )


with open(
    "index.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        data,
        f,
        indent=4,
        ensure_ascii=False
    )


print("Generated index.json")
