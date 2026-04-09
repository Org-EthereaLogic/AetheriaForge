# forge
Contract-driven transformation and coherence-scoring engine. Transforms source
records into schema-contract output and scores the result with Shannon entropy.
For contract-backed runs, the coherence score follows the schema's declared
source lineage so renamed targets, multi-source derivations, and intentional
projection are evaluated against the target contract instead of raw by-name
column overlap.
