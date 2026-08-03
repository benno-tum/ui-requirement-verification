#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
thesis_dir="$(cd "${script_dir}/.." && pwd)"
repo_dir="$(cd "${thesis_dir}/.." && pwd)"
source_file="${1:-${repo_dir}/docs/thesis_first_draft.md}"
chapter_dir="${thesis_dir}/chapters"
notes_dir="${thesis_dir}/notes"

if ! command -v pandoc >/dev/null 2>&1; then
  echo "pandoc is required to synchronize the Markdown draft." >&2
  exit 1
fi

if [[ ! -f "${source_file}" ]]; then
  echo "Markdown source not found: ${source_file}" >&2
  exit 1
fi

mkdir -p "${chapter_dir}" "${notes_dir}"
tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/thesis-sync.XXXXXX")"
trap 'rm -rf "${tmp_dir}"' EXIT

chapter_files=(
  "01_introduction"
  "02_foundations_related_work"
  "03_research_design"
  "04_verification_approach"
  "05_dataset_annotation"
  "06_evaluation"
  "07_discussion"
  "08_conclusion"
)

normalize_citations() {
  local file="$1"

  LC_ALL=C perl -0pi -e '
    s/\(Kretzer et al\., 2025; Kolthoff et al\., 2025; Massenon, Gambo, and Khan, 2026\)/[\@kretzer2025; \@kolthoff2025guispector; \@massenon2026]/g;
    s/\(Kretzer et al\., 2025; Massenon, Gambo, and Khan, 2026\)/[\@kretzer2025; \@massenon2026]/g;
    s/\(Hendrickx et al\.,\s+2024; Wen et al\., 2025\)/[\@hendrickx2024; \@wen2025]/g;
    s/\(Nass, Alégroth, and Feldt, 2021\)/[\@nass2021]/g;
    s/\(Berry, Kamsties, and Krieger, 2003\)/[\@berry2003]/g;
    s/\(Ferrari, Spagnolo, and Gnesi, 2017\)/[\@ferrari2017]/g;
    s/\(Field and Welsh, 2007\)/[\@fieldwelsh2007]/g;
    s/\(Massenon, Gambo, and Khan, 2026\)/[\@massenon2026]/g;
    s/\(Baltes et al\., 2026\)/[\@baltes2026]/g;
    s/\(Becker et al\., 2025\)/[\@becker2025]/g;
    s/\(Cheng et al\., 2024\)/[\@cheng2024]/g;
    s/\(Cleland-Huang et al\., 2014\)/[\@clelandhuang2014]/g;
    s/\(Deng et al\., 2023\)/[\@deng2023]/g;
    s/\(Ferrari et al\., 2017\)/[\@ferrari2017]/g;
    s/\(Gervasi et al\., 2019\)/[\@gervasi2019]/g;
    s/\(Gou et al\., 2025\)/[\@gou2025]/g;
    s/\(Hendrickx et al\., 2024\)/[\@hendrickx2024]/g;
    s/\(Jimenez et al\., 2024\)/[\@jimenez2024]/g;
    s/\(Kolthoff et al\., 2025\)/[\@kolthoff2025guispector]/g;
    s/\(Kretzer et al\., 2025\)/[\@kretzer2025]/g;
    s/\(Kwa et al\., 2025\)/[\@kwa2025]/g;
    s/\(Rawles et al\., 2023\)/[\@rawles2023]/g;
    s/\(Wen et al\., 2025\)/[\@wen2025]/g;
    s/\(Yang et al\., 2023\)/[\@yang2023]/g;
    s/\(Zheng et al\., 2024\)/[\@zheng2024]/g;
    s/\bBecker et al\.\s+\(2025\)/\@becker2025/g;
    s/\bBaltes\s+et al\.\s+\(2026\)/\@baltes2026/g;
    s/\bBerry, Kamsties, and Krieger \(2003\)/\@berry2003/g;
    s/\bCheng et al\. \(2024\)/\@cheng2024/g;
    s/\bCleland-Huang et al\. \(2014\)/\@clelandhuang2014/g;
    s/\bDeng et al\. \(2023\)/\@deng2023/g;
    s/\bFerrari et al\. \(2017\)/\@ferrari2017/g;
    s/\bField and Welsh \(2007\)/\@fieldwelsh2007/g;
    s/\bGervasi et al\. \(2019\)/\@gervasi2019/g;
    s/\bGou et al\. \(2025\)/\@gou2025/g;
    s/\bHendrickx et al\. \(2024\)/\@hendrickx2024/g;
    s/\bJimenez et al\. \(2024\)/\@jimenez2024/g;
    s/\bKolthoff et al\. \(2025\)/\@kolthoff2025guispector/g;
    s/\bKretzer et al\. \(2025\)/\@kretzer2025/g;
    s/\bKwa et al\. \(2025\)/\@kwa2025/g;
    s/\bMassenon, Gambo, and Khan \(2026\)/\@massenon2026/g;
    s/\bNass, Alégroth, and Feldt \(2021\)/\@nass2021/g;
    s/\bRawles et al\. \(2023\)/\@rawles2023/g;
    s/\bWen et al\. \(2025\)/\@wen2025/g;
    s/\bYang et al\. \(2023\)/\@yang2023/g;
    s/\bZheng et al\. \(2024\)/\@zheng2024/g;
  ' "${file}"
}

for index in "${!chapter_files[@]}"; do
  chapter_number="$((index + 1))"
  chapter_name="${chapter_files[index]}"
  markdown_file="${tmp_dir}/${chapter_name}.md"
  latex_file="${chapter_dir}/${chapter_name}.tex"

  awk -v chapter="${chapter_number}" '
    $0 ~ "^## " chapter " " {capture = 1}
    capture && $0 ~ "^## [0-9]+ " && $0 !~ "^## " chapter " " {exit}
    capture && /^## References Used in This Draft/ {exit}
    capture {print}
  ' "${source_file}" > "${markdown_file}"

  if [[ ! -s "${markdown_file}" ]]; then
    echo "Could not extract chapter ${chapter_number} from ${source_file}" >&2
    exit 1
  fi

  sed -E \
    -e "s/^## ${chapter_number} (.*)$/# \\1/" \
    -e "s/^### ${chapter_number}\\.[0-9]+ (.*)$/## \\1/" \
    -e "s/^#### (.*)$/### \\1/" \
    "${markdown_file}" > "${markdown_file}.normalized"
  mv "${markdown_file}.normalized" "${markdown_file}"

  normalize_citations "${markdown_file}"

  {
    pandoc "${markdown_file}" \
      --from='markdown+pipe_tables+strikeout+task_lists+tex_math_dollars+tex_math_single_backslash' \
      --to=latex \
      --top-level-division=chapter \
      --biblatex \
      --wrap=preserve
  } > "${latex_file}"

  # Keep the compact comparison tables in the document's normal reading
  # orientation. The generated proportional columns already span \linewidth;
  # forcing every longtable into pdflscape created mostly empty rotated pages.
  LC_ALL=C perl -0pi -e '
    s/PARTIALLY\\_FULFILLED/PARTIALLY\\_\\allowbreak FULFILLED/g;
    s/PARTIALLY\\_UI\\_VERIFIABLE/PARTIALLY\\_\\allowbreak UI\\_\\allowbreak VERIFIABLE/g;
    s/WHOLE\\_SCREEN\\_OR\\_TRANSITION/WHOLE\\_\\allowbreak SCREEN\\_\\allowbreak OR\\_\\allowbreak TRANSITION/g;
    s/NO\\_VISIBLE\\_REGION/NO\\_\\allowbreak VISIBLE\\_\\allowbreak REGION/g;
  ' "${latex_file}"
done

# These figures are authored as standalone TikZ assets but must remain linked
# from the canonical Markdown source. Fail immediately if synchronization would
# silently orphan any retained asset again.
if ! grep -Fq '\input{figures/evidence_first_architecture}' \
  "${chapter_dir}/04_verification_approach.tex"; then
  echo "Architecture figure was lost during Markdown synchronization." >&2
  exit 1
fi

if ! grep -Fq '\input{figures/benchmark_construction_funnel}' \
  "${chapter_dir}/05_dataset_annotation.tex"; then
  echo "Benchmark-construction figure was lost during Markdown synchronization." >&2
  exit 1
fi

if ! grep -Fq '\input{figures/amtrak_running_example}' \
  "${chapter_dir}/05_dataset_annotation.tex"; then
  echo "Amtrak running-example figure was lost during Markdown synchronization." >&2
  exit 1
fi

{
  printf '# Pending notes retained from the Markdown source\n\n'
  printf 'These comments are intentionally excluded from the compiled thesis. Resolve them in `docs/thesis_first_draft.md`, then run `make sync` again.\n\n'
  awk '
    /<!--/ {inside = 1; block += 1; print "## Note " block "\n"}
    inside {print}
    /-->/ {inside = 0; print ""}
  ' "${source_file}"
} > "${notes_dir}/pending_from_markdown.md"

echo "Synchronized 8 chapters from ${source_file}"
