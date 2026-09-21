# A Project File Will Not Open

SYMPTOM: File > Open... on a chosen file ends in an error message instead of opening the project.

CAUSE: one of three things - the file is not valid JSON (a parse error), the `format` field is not `"EPW_SYNOPTIC"` (it is a file from a different program or a different format, e.g. the EPW_PROJECT one mentioned in [10.1](help://synoptic/file-contents)), or `schema_version` is higher than this editor build supports ([10.2](help://synoptic/file-versioning)).

FIX: read the exact error text in the Messages panel - each of the three cases has its own, specific message. A file with too new a version needs a newer editor build; a wrong format is not a file from this program at all.
