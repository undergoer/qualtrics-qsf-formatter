import json
from datetime import datetime

input_file = "survey_cleaned_consistent_FULL.txt"
survey_title = "AI IN RESEARCH (AIR) \u2013 FACULTY SURVEY"

questions = []

# Parser state
current_question = None
current_section = None
parse_mode = None  # None | 'text' | 'choices' | 'rows' | 'scalelabels'

SKIP_PREFIXES = ("===", "SURVEY INTRODUCTION", "[Block", "[/Block")

def save_question(q):
    if q and q.get("QIDLabel"):
        questions.append(q)

current_branch_logic = None  # DisplayLogic string inherited from [Branch] If: ...

with open(input_file, "r", encoding="utf-8") as f:
    for raw in f:
        line = raw.strip()
        if not line:
            parse_mode = None
            continue
        if line == survey_title:
            continue
        if any(line.startswith(p) for p in SKIP_PREFIXES):
            parse_mode = None
            continue
        if line == "[/Branch]":
            current_branch_logic = None
            parse_mode = None
            continue
        if line == "[Branch]":
            parse_mode = None
            continue
        if line.startswith("If:") and current_branch_logic is None:
            # e.g. "If: A1 == Faculty of Architecture, Building and Planning"
            cond = line[3:].strip()
            current_branch_logic = f"Show if {cond}"
            parse_mode = None
            continue
        if line.startswith("PART ") or line.startswith("CLOSING"):
            current_section = line
            parse_mode = None
            continue
        if line.startswith("Purpose:"):
            parse_mode = None
            continue
        if line.startswith("QID:"):
            save_question(current_question)
            current_question = {
                "QIDLabel": line.split(":", 1)[1].strip(),
                "Section": current_section,
                "QuestionType": "",
                "QuestionText": "",
                "Choices": [],
                "Rows": [],
                "ScaleLabels": {},
                "Metadata": {}
            }
            if current_branch_logic:
                current_question["Metadata"]["DisplayLogic"] = current_branch_logic
            parse_mode = None
            continue
        if current_question is None:
            continue
        if line.startswith("[QuestionType:"):
            raw_meta = line.split("[QuestionType:", 1)[1].rstrip("]").strip()
            current_question["QuestionType"] = raw_meta
            if "|" in raw_meta:
                parts = [p.strip() for p in raw_meta.split("|")]
                for part in parts[1:]:
                    if ":" in part:
                        k, v = part.split(":", 1)
                        current_question["Metadata"][k.strip()] = v.strip()
            parse_mode = None
            continue
        if line.startswith("[DisplayLogic:"):
            logic = line.split("[DisplayLogic:", 1)[1].rstrip("]").strip()
            current_question["Metadata"]["DisplayLogic"] = logic
            parse_mode = None
            continue
        if line == "Choices:":
            parse_mode = "choices"
            continue
        if line == "Rows:":
            parse_mode = "rows"
            continue
        if line == "ScaleLabels:":
            parse_mode = "scalelabels"
            continue
        if line.startswith("QuestionText:"):
            current_question["QuestionText"] = line.split(":", 1)[1].strip()
            parse_mode = "text"
            continue
        if line.startswith("- "):
            item = line[2:].strip()
            if parse_mode == "rows":
                current_question["Rows"].append(item)
            elif parse_mode == "choices":
                current_question["Choices"].append(item)
            elif parse_mode == "text":
                qt = current_question["QuestionType"].upper()
                if "DESCRIPTIVE" in qt or (not current_question["Choices"] and not current_question["Rows"]):
                    current_question["QuestionText"] += f"<br>\u2022 {item}"
                else:
                    current_question["Choices"].append(item)
            else:
                current_question["Choices"].append(item)
            continue
        if parse_mode == "scalelabels" and "=" in line and line[0].isdigit():
            num, label = line.split("=", 1)
            current_question["ScaleLabels"][num.strip()] = label.strip()
            continue
        if parse_mode == "text" and not line.startswith("["):
            current_question["QuestionText"] += " " + line
            continue
        qt = current_question.get("QuestionType", "").upper()
        if "DESCRIPTIVE" in qt and not line.startswith("[") and not line.startswith("QID:"):
            if current_question["QuestionText"]:
                current_question["QuestionText"] += " " + line
            else:
                current_question["QuestionText"] = line
            parse_mode = "text"
            continue

save_question(current_question)

# ─── Qualtrics type mapping ───────────────────────────────────────────────────

def get_qualtrics_type(raw_type, has_rows=False):
    raw = raw_type.upper()
    base = raw.split("|")[0].strip()
    if "DESCRIPTIVE" in base:
        return "DB", "TB", None
    if "MATRIX" in base or has_rows:
        return "Matrix", "Likert", "SingleAnswer"
    if "SCALE" in base or "RATING" in base:
        return "MC", "SAVR", "TX"
    if "RANK" in base:
        return "RO", "Rank", None
    if "TEXT" in base or "OPEN" in base or "TE" in base:
        return "TE", "ML", None
    if "MC" in base or "MULTIPLE CHOICE" in base:
        if "MULTI" in raw:
            return "MC", "MAVR", "TX"
        return "MC", "SAVR", "TX"
    return "TE", "ML", None

# ─── IDs ─────────────────────────────────────────────────────────────────────

SURVEY_ID    = "SV_surveyimport001"
OWNER_ID     = "UR_surveyimport001"
BRAND_ID     = "melbourneuni"
RS_ID        = "RS_surveyimport001"
BLOCK_ID     = "BL_surveyimport01"

# ─── DB question HTML formatter ──────────────────────────────────────────────

def html_entities(s):
    """Convert common Unicode characters to HTML entities for Qualtrics."""
    return (s
        .replace("–", "&ndash;")
        .replace("—", "&mdash;")
        .replace("'", "&rsquo;")
        .replace("\u2019", "&rsquo;")
        .replace("\u2018", "&lsquo;")
        .replace("\u201c", "&ldquo;")
        .replace("\u201d", "&rdquo;")
        .replace("•", "&bull;")
    )

def build_db_html(text):
    """Format a descriptive block as h4 with bullet points and HTML entities."""
    parts = text.split("<br>•")
    main_text = html_entities(parts[0].strip())

    if len(parts) == 1:
        return f"<h4>{main_text}</h4>"

    # Format each bullet as indented bullet with <br /> separator
    bullet_lines = []
    for part in parts[1:]:
        bullet_lines.append(f"&nbsp; &nbsp; &bull; {html_entities(part.strip())}")
    bullets_html = "<br />\n".join(bullet_lines)

    return (
        f"<h4>{main_text}</h4>\n\n"
        f"<div>&nbsp;</div>\n\n"
        f"<h4>{bullets_html}</h4>"
    )

# ─── Build question elements ──────────────────────────────────────────────────

survey_elements = []

# Pre-build complete maps before element loop so DisplayLogic can reference any question
qid_map = {q["QIDLabel"]: f"QID{idx}" for idx, q in enumerate(questions, start=1)}
choice_lookup = {}  # {label: {choice_text_lower: choice_idx}}
for q in questions:
    choices = q["Rows"] if q["Rows"] else q["Choices"]
    if choices:
        choice_lookup[q["QIDLabel"]] = {ch.lower(): i + 1 for i, ch in enumerate(choices)}

for idx, question in enumerate(questions, start=1):
    numeric_qid = f"QID{idx}"

    has_rows = bool(question["Rows"])
    qt, selector, sub_selector = get_qualtrics_type(question["QuestionType"], has_rows)

    choice_source = question["Rows"] if has_rows else question["Choices"]

    # ── Detect "Group: Sub-item" pattern ─────────────────────────────────────
    prefix_counts = {}
    for ch in choice_source:
        clean = ch.replace("[TextEntry]", "").strip()
        if ": " in clean:
            prefix = clean.split(": ", 1)[0]
            prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
    group_prefixes = {p for p, n in prefix_counts.items() if n >= 2}

    # Build ordered group list and map prefix -> (cg_key, choice indices)
    group_key_map = {}      # prefix -> "cg_N"
    group_choice_ids = {}   # "cg_N" -> [cidx, ...]
    group_labels = {}       # "cg_N" -> display label string
    cg_order = []           # ["cg_1", "cg_2", ...]
    next_cg = 1
    for ch in choice_source:
        clean = ch.replace("[TextEntry]", "").strip()
        if ": " in clean:
            prefix = clean.split(": ", 1)[0]
            if prefix in group_prefixes and prefix not in group_key_map:
                key = f"cg_{next_cg}"
                group_key_map[prefix] = key
                group_choice_ids[key] = []
                group_labels[key] = prefix
                cg_order.append(key)
                next_cg += 1

    choices_obj = {}
    choice_order = []
    for cidx, ch in enumerate(choice_source, start=1):
        has_text_entry = "[TextEntry]" in ch
        ch_lower = ch.lower()
        if not has_text_entry and "other" in ch_lower and ("specify" in ch_lower or "please" in ch_lower):
            has_text_entry = True
        display = ch.replace("[TextEntry]", "").strip()

        # Strip group prefix, record choice in its group
        if ": " in display and display.split(": ", 1)[0] in group_prefixes:
            prefix = display.split(": ", 1)[0]
            display = display.split(": ", 1)[1]
            group_choice_ids[group_key_map[prefix]].append(cidx)

        choice_dict = {"Display": display}
        if has_text_entry:
            choice_dict["TextEntry"] = "true"
            choice_dict["TextEntrySize"] = "Small"
        choices_obj[str(cidx)] = choice_dict
        choice_order.append(cidx)


    answers_obj = {}
    answer_order = []
    if question["ScaleLabels"]:
        for aidx, (k, v) in enumerate(sorted(question["ScaleLabels"].items(), key=lambda x: int(x[0])), start=1):
            answers_obj[str(aidx)] = {"Display": v}
            answer_order.append(aidx)

    q_text = question["QuestionText"] or f"[{question['QIDLabel']}]"
    q_text_html = f"<h4>{q_text}</h4>"
    q_desc = q_text[:100]

    payload = {
        "QuestionText": q_text_html,
        "DefaultChoices": False,
        "DataExportTag": question["QIDLabel"],
        "QuestionType": qt,
        "Selector": selector,
        "DataVisibility": {"Private": False, "Hidden": False},
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "QuestionDescription": q_desc,
        "Validation": {
            "Settings": {
                "ForceResponse": "OFF",
                "Type": "None"
            }
        },
        "GradingData": [],
        "Language": [],
        "NextChoiceId": len(choice_source) + 1,
        "NextAnswerId": 1,
        "QuestionID": numeric_qid,
    }

    if sub_selector:
        payload["SubSelector"] = sub_selector

    if qt == "DB":
        payload["ChoiceOrder"] = []
        payload["Validation"] = {"Settings": {"Type": "None"}}

    if choices_obj and qt not in ("DB", "TE"):
        payload["Choices"] = choices_obj
        payload["ChoiceOrder"] = choice_order
        if cg_order:
            cg_groups = {}
            for key in cg_order:
                label = group_labels[key]
                cg_groups[key] = {
                    "ChoiceGroupOrder": group_choice_ids[key],
                    "GroupLabel": (
                        f'<br />\n<span style="color:#000000;">'
                        f'<span style="font-size:16px;">{label}</span></span>'
                    ),
                    "Options": {"Selection": "MAWithinQuestion"}
                }
            payload["ChoiceGroups"] = cg_groups
            payload["ChoiceGroupOrder"] = cg_order

    if answers_obj:
        payload["Answers"] = answers_obj
        payload["AnswerOrder"] = answer_order

    if qt == "TE":
        payload["SearchSource"] = {"AllowFreeResponse": "false"}

    if "DisplayLogic" in question["Metadata"]:
        logic_str = question["Metadata"]["DisplayLogic"]
        if "==" in logic_str:
            left, right = logic_str.split("==", 1)
            # Strip "Show if" prefix to get the referenced question label
            ref_label = left.strip()
            for prefix in ("Show if ", "show if ", "Show If "):
                ref_label = ref_label.replace(prefix, "")
            ref_label = ref_label.strip()
            ref_value = right.strip()

            ref_qid = qid_map.get(ref_label)
            if ref_qid:
                # Find which choice index matches the value
                ref_choices = choice_lookup.get(ref_label, {})
                choice_idx = ref_choices.get(ref_value.lower(), 1)
                locator = f"q://{ref_qid}/SelectableChoice/{choice_idx}"

                payload["DisplayLogic"] = {
                    "0": {
                        "0": {
                            "ChoiceLocator": locator,
                            "LeftOperand": locator,
                            "LogicType": "Question",
                            "Operator": "Selected",
                            "QuestionID": ref_qid,
                            "QuestionIsInLoop": "no",
                            "RightOperand": None,
                            "Type": "Expression"
                        },
                        "Type": "If"
                    },
                    "Type": "BooleanExpression",
                    "inPage": False
                }

    survey_elements.append({
        "SurveyID": SURVEY_ID,
        "Element": "SQ",
        "PrimaryAttribute": numeric_qid,
        "SecondaryAttribute": q_desc,
        "TertiaryAttribute": None,
        "Payload": payload
    })

# ─── Block ────────────────────────────────────────────────────────────────────

block_elements = [
    {"Type": "Question", "QuestionID": e["PrimaryAttribute"]}
    for e in survey_elements
]

survey_elements.append({
    "SurveyID": SURVEY_ID,
    "Element": "BL",
    "PrimaryAttribute": "Survey Blocks",
    "SecondaryAttribute": None,
    "TertiaryAttribute": None,
    "Payload": {
        "1": {
            "Type": "Standard",
            "SubType": "",
            "Description": "Block 1",
            "ID": BLOCK_ID,
            "BlockElements": block_elements
        }
    }
})

# ─── Flow ─────────────────────────────────────────────────────────────────────

survey_elements.append({
    "SurveyID": SURVEY_ID,
    "Element": "FL",
    "PrimaryAttribute": "Survey Flow",
    "SecondaryAttribute": None,
    "TertiaryAttribute": None,
    "Payload": {
        "Flow": [{"ID": BLOCK_ID, "Type": "Standard", "FlowID": "FL_2"}],
        "Properties": {"Count": 1},
        "FlowID": "FL_1",
        "Type": "Root"
    }
})

# ─── PROJ ─────────────────────────────────────────────────────────────────────

survey_elements.append({
    "SurveyID": SURVEY_ID,
    "Element": "PROJ",
    "PrimaryAttribute": "CORE",
    "SecondaryAttribute": None,
    "TertiaryAttribute": "1.1.0",
    "Payload": {"ProjectCategory": "CORE", "SchemaVersion": "1.1.0"}
})

# ─── QC (Question Count) ──────────────────────────────────────────────────────

survey_elements.append({
    "SurveyID": SURVEY_ID,
    "Element": "QC",
    "PrimaryAttribute": "Survey Question Count",
    "SecondaryAttribute": str(len(questions)),
    "TertiaryAttribute": None,
    "Payload": None
})

# ─── RS (Response Set) ────────────────────────────────────────────────────────

survey_elements.append({
    "SurveyID": SURVEY_ID,
    "Element": "RS",
    "PrimaryAttribute": RS_ID,
    "SecondaryAttribute": "Default Response Set",
    "TertiaryAttribute": None,
    "Payload": None
})

# ─── SCO (Scoring) ────────────────────────────────────────────────────────────

survey_elements.append({
    "SurveyID": SURVEY_ID,
    "Element": "SCO",
    "PrimaryAttribute": "Scoring",
    "SecondaryAttribute": None,
    "TertiaryAttribute": None,
    "Payload": {
        "ScoringCategories": [],
        "ScoringCategoryGroups": [],
        "ScoringSummaryCategory": None,
        "ScoringSummaryAfterQuestions": 0,
        "ScoringSummaryAfterSurvey": 0,
        "DefaultScoringCategory": None,
        "AutoScoringCategory": None
    }
})

# ─── SO (Survey Options) ──────────────────────────────────────────────────────

survey_elements.append({
    "SurveyID": SURVEY_ID,
    "Element": "SO",
    "PrimaryAttribute": "Survey Options",
    "SecondaryAttribute": None,
    "TertiaryAttribute": None,
    "Payload": {
        "BackButton": "false",
        "SaveAndContinue": "true",
        "SurveyProtection": "PublicSurvey",
        "BallotBoxStuffingPrevention": "false",
        "NoIndex": "Yes",
        "SecureResponseFiles": "true",
        "SurveyExpiration": "None",
        "SurveyTermination": "DefaultMessage",
        "Header": "",
        "Footer": "",
        "ProgressBarDisplay": "None",
        "PartialData": "+1 week",
        "ValidationMessage": "",
        "PreviousButton": "",
        "NextButton": "",
        "SurveyTitle": survey_title,
        "SkinLibrary": BRAND_ID,
        "SkinType": "component",
        "Skin": {"brandingId": None, "templateId": "*base", "overrides": None},
        "NewScoring": 1,
        "SurveyName": survey_title,
        "ProtectSelectionIds": True
    }
})

# ─── STAT ─────────────────────────────────────────────────────────────────────

survey_elements.append({
    "SurveyID": SURVEY_ID,
    "Element": "STAT",
    "PrimaryAttribute": "Survey Statistics",
    "SecondaryAttribute": None,
    "TertiaryAttribute": None,
    "Payload": {"MobileCompatible": True, "ID": "Survey Statistics"}
})

# ─── Survey Entry ─────────────────────────────────────────────────────────────

now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

qsf = {
    "SurveyEntry": {
        "SurveyID": SURVEY_ID,
        "SurveyName": survey_title,
        "SurveyDescription": None,
        "SurveyOwnerID": OWNER_ID,
        "SurveyBrandID": BRAND_ID,
        "DivisionID": None,
        "SurveyLanguage": "EN",
        "SurveyActiveResponseSet": RS_ID,
        "SurveyStatus": "Active",
        "SurveyStartDate": "0000-00-00 00:00:00",
        "SurveyExpirationDate": "0000-00-00 00:00:00",
        "SurveyCreationDate": now_str,
        "CreatorID": OWNER_ID,
        "LastModified": now_str,
        "LastAccessed": "0000-00-00 00:00:00",
        "LastActivated": "0000-00-00 00:00:00",
        "Deleted": None
    },
    "SurveyElements": survey_elements
}

output_file = "parsed_survey.qsf"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(qsf, f, indent=2, ensure_ascii=False)

print(f"Saved to {output_file}.")
print(f"Total questions: {len(questions)}")
print("\nQuestion audit:")
for e in survey_elements:
    if e["Element"] == "SQ":
        p = e["Payload"]
        text = p["QuestionDescription"][:65] if p["QuestionDescription"] else "*** EMPTY ***"
        nc = len(p.get("Choices", {}))
        na = len(p.get("Answers", {}))
        print(f"  {e['PrimaryAttribute']:6s} [{p['QuestionType']:7s}] C={nc:2d} A={na:2d}  {text}")
