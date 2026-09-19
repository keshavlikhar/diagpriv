"""Reviewed, case-specific provenance for prospective Incident 003 v3 Stage 3.

These values were checked against the historical v11 input freeze before v13
was implemented. The v5 requirement hashes resolve the existing generic
rubric against the same eight selected development cases.
"""

STAGE3_MANIFEST_VERSION = "raw-rca-manifest-v13"
STAGE3_TRANSFORMATION_SHA256 = (
    "fc564bb585f3f30e0482c206b061d096a49c3bc824965043f9eeb3ff12d71f7b"
)
STAGE3_PROMPT_SHA256 = (
    "a2fc07481c9cd33776086d16cd76fafaa27c2fdf162f4ae634885187d0d22139"
)

STAGE3_MODEL_INPUT_SHA256_BY_CASE_ID = {
    "1319:target": "a14a79f2c923e8a674ca5f6e88c07434841eadec509a8f457d5bf2428963037e",
    "1319:temporal_twin": "ad9400cf344a34b91ed7a3f5c0125c9f1c2c9b59f5737db1f69fa5016b55b9ec",
    "1299:target": "7d3bbafc8e003908f529259c9038e5e7e67c3c31ee6790c6a995d3b20ce1146b",
    "1299:temporal_twin": "7e8b263aff8e85d5bad358992001406bcdca87a9019370dff3b51d49552f2672",
    "1387:target": "0a66accda0e5aaba981a743526914ae81f6d3f79d712e91fd5a3ea7b57a26f8c",
    "1387:temporal_twin": "674aa91310a1b9185acf6e3c4276a69eb592d31320e7253d9420b2ae5f3dfcbb",
    "1222:target": "854c91718478adfa302f187728dc4b5a356b5f366b25d7867e3aa3d770d45a4f",
    "1222:temporal_twin": "49cb4c19fcac5eb9eaf388bb914d9abb6c7b77b3720973307fa7dc511f014c07",
}

STAGE3_V5_REQUIREMENT_SHA256_BY_CASE_ID = {
    "1319:target": "c68aa89d9b9414a520435eea7f0830a4f7ce8e1e0b56fd09d5feaa995381593d",
    "1319:temporal_twin": "745df9f32e9768c064a61dbce43d424dfbd62c544d62cd33c7d21c2f9cf775cd",
    "1299:target": "832a09456766ee9fbdb5796327be33375190435b8db18a63b8af85587c3d2ca5",
    "1299:temporal_twin": "9576f9e5271054daeb41dc6ef8e9654b4ec7a0630dbdcbacd89010b909874794",
    "1387:target": "d5d6bee92d6db457153f8f97325ea295552b53330e8366f7fd7e0b692f415579",
    "1387:temporal_twin": "189c2295b1b7eb69ad9d0c2b6f91cec864ff17b39f0466051a803fc31cdf5c09",
    "1222:target": "6a6e4571351b6d726c65588e19f44bfd0d179ece291861b8071644a6c81c732b",
    "1222:temporal_twin": "e09c002225b8e1bc35098e56682a66c4f74ac72c6c9c6e2cc2edb3edd60484a3",
}
