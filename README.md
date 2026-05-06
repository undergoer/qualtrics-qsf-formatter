# Creating a Qualtrics Survey from a Custom Format

## Steps
1. Saved Word document as a .txt file.
2. Did some slight formatting and sign-posting to make it easier to parse.
3. Used Copilot (Microsoft 365) to find inconsistent formatting
4. Used Copilot (Microsoft 365) to reformat .txt file and give advice on how to format given the logic required
5. Used Copilot (Github) to write a Python script to convert the .txt file to a .qsf file.

## Prompts

Copilot (Microsoft 365):

    I have this survey that I want to convert to qsf Qualtrics json format. I have some logic in there so that for when participants choose a specific answer to A1 -- for these, I have denoted the "##start" and "##end" to these sub-sections with the conditions just before it.
    First I want you to flag any formatting that is inconsistent and then let me know how to encode a qsf to reflect this logic based on A1's answer.

Copilot (Microsoft 365) asks what I want to do next I prompt with:

    Ultimately I want a lightweight script that would ingest this text and create a qsf json format - I want one survey that branches out for A1, but before you do that can you produce another .txt file where the numbering is consistent, and the formatting is consistent. Check for inconsistencies in
       1. multiple choice questions
       2. scale questions (choosing a number on a scale for degree of agreement or disagreement on the question)
       3. where the answer is text-based (what should the field say? at the moment these are just lines)
       4. single choice
       5. nested choices - maybe convert these to conditional questions?

Copilot (Github):

    I want to ingest the content in the file "survey_cleaned_consistent_FULL.txt"

The file "survey_cleaned_consistent_FULL.txt" contains survey data with structured questions and metadata. To ingest this content, I can write a script in "encode-qsf.py" to parse and process the file. Would you like me to proceed with implementing this? 

    yes

I had some manual editing to do, but it was minimal.