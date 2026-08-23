# Documentation boundary

Elan's public documentation explains the product and how to use it. Working
strategy belongs in the private `Accelerate-lux/elan-project` repository.

## Public documentation

The public site may contain:

- deliberately approved product positioning and capability status
- learning material, guides, runnable examples, and API/runtime reference
- user-facing roadmap statements labeled with the canonical maturity taxonomy
- primary-source comparisons that have been deliberately reviewed for public
  release

The comparison pages in this site are approved product documentation. They
describe user-relevant programming-model differences; they are not the source
notes, positioning hypotheses, or prioritization criteria used to prepare those
pages.

## Private strategy

The private project repository owns:

- exploratory competitive research and unpublished comparison drafts
- adoption strategy, distribution plans, campaign material, and Clinic planning
- success thresholds, stop conditions, and other internal decision criteria
- demo prioritization, internal positioning hypotheses, and unpublished brand
  research
- coding-agent evaluation results until they are deliberately approved for
  publication

Technical implementation notes may remain beside the source under
`docs/internals/`, but MkDocs excludes that directory. Those notes must not
contain the private strategy categories above.

## Build inclusion boundary

`mkdocs.yml` defines the public site boundary:

- `nav` is the reviewed Markdown page list;
- `exclude_docs` contains source-adjacent technical and legacy material that is
  intentionally not published;
- `mkdocs build --strict` fails when a new Markdown page is neither reviewed
  into navigation nor deliberately excluded.

`docs/llms.txt` is a separate curated index for coding agents. A page is not
added there merely because it exists in the public repository or built site.

## Review checklist

Before merging documentation changes:

1. Classify each new document as public product documentation, technical design,
   or private strategy.
2. Relocate private strategy to `elan-project`; exclusion from MkDocs alone is
   not sufficient.
3. Require a deliberate publication decision for new comparison material.
4. Add public pages to `nav`, or add non-public technical pages to
   `exclude_docs`.
5. Add only stable, agent-useful entry points to `docs/llms.txt`.
6. Run `mkdocs build --strict` and inspect the changed public claims.
