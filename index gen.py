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

            lookup[make_alias_key(name)] = [
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
            "("
            + re.escape(token)
            + "|"
            + re.escape(arabic)
            + ")"
        )

    if token in ARABIC_TO_ROMAN:

        roman = ARABIC_TO_ROMAN[token]

        return (
            "("
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

    return " ".join(
        make_token_pattern(part)
        for part in parts
    )


def make_title_patterns(title):
    patterns = []

    full_pattern = make_title_pattern(title)

    if full_pattern:
        patterns.append(full_pattern)

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
                + " "
                + subtitle_pattern
            )

            patterns.append(
                main_pattern
                + r"\s*-\s*"
                + subtitle_pattern
            )

    return list(
        dict.fromkeys(patterns)
    )


def is_prefix_title(title, all_titles):
    title_parts = normalise_text(title)

    if not title_parts:
        return False

    for other_title in all_titles:

        if other_title.lower() == title.lower():
            continue

        other_parts = normalise_text(other_title)

        if len(other_parts) <= len(title_parts):
            continue

        if other_parts[:len(title_parts)] == title_parts:
            return True

    return False


def make_regex(
    title,
    platform,
    bracket_extras=None,
    aliases=None,
    all_titles=None
):
    bracket_extras = bracket_extras or []
    aliases = aliases or []
    all_titles = all_titles or []

    search_titles = [title]

    for alias in aliases:

        if alias.lower() == title.lower():
            continue

        if not any(
            alias.lower() == existing.lower()
            for existing in search_titles
        ):
            search_titles.append(alias)

    main_patterns = []

    for search_title in search_titles:

        patterns = make_title_patterns(
            search_title
        )

        needs_end_anchor = is_prefix_title(
            search_title,
            all_titles
        )

        for pattern in patterns:

            if needs_end_anchor:
                pattern = "^" + pattern + "$"

            main_patterns.append(
                pattern
            )

    patterns = list(main_patterns)

    for extra in bracket_extras:

        extra_pattern = make_title_pattern(
            extra
        )

        if not extra_pattern:
            continue

        for pattern in main_patterns:

            clean_pattern = pattern

            if clean_pattern.startswith("^"):
                clean_pattern = clean_pattern[1:]

            if clean_pattern.endswith("$"):
                clean_pattern = clean_pattern[:-1]

            patterns.append(
                clean_pattern
                + " "
                + extra_pattern
            )

    platform_pattern = make_title_pattern(
        platform
    )

    if platform_pattern:

        base_patterns = list(patterns)

        for pattern in base_patterns:

            clean_pattern = pattern

            if clean_pattern.startswith("^"):
                clean_pattern = clean_pattern[1:]

            if clean_pattern.endswith("$"):
                clean_pattern = clean_pattern[:-1]

            patterns.append(
                platform_pattern
                + " "
                + clean_pattern
            )

    patterns = list(
        dict.fromkeys(patterns)
    )

    if not patterns:
        return "^$"

    if len(patterns) == 1:
        return patterns[0]

    return (
        "("
        + "|".join(patterns)
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


platform_entries = {}
all_titles = []


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

            aliases = ALIAS_LOOKUP.get(
                make_alias_key(display_name),
                []
            )

            relative_path = os.path.relpath(
                full_path,
                "."
            ).replace(
                "\\",
                "/"
            )

            entry = {
                "game": display_name,
                "file": relative_path,
                "_platform": detected_platform,
                "_brackets": bracket_extras,
                "_aliases": aliases
            }

            entries.append(entry)
            all_titles.append(display_name)

    platform_entries[platform] = entries


all_titles = list(
    dict.fromkeys(
        all_titles
    )
)


for platform in sorted(
    platform_entries,
    key=str.lower
):

    entries = []

    for entry in platform_entries[platform]:

        regex = make_regex(
            entry["game"],
            entry["_platform"],
            entry["_brackets"],
            entry["_aliases"],
            all_titles
        )

        entries.append({
            "game": entry["game"],
            "file": entry["file"],
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
