"""
Template Engine for HTML, JSON, CSV, and Markdown Rendering.
"""

from typing import Any, Dict
import json
from akaal.reporting.models.report import ReportArtifact


class TemplateEngine:
    """Enterprise Reporting Template Engine."""

    def render_html(self, artifact: ReportArtifact) -> str:
        sections_html = ""
        for s in artifact.sections:
            sections_html += f"<section><h2>{s.title}</h2><p>{s.content}</p></section>\n"

        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{artifact.metadata.title}</title>
    <style>body {{ font-family: sans-serif; margin: 2rem; }} h1 {{ color: #1a365d; }}</style>
</head>
<body>
    <h1>{artifact.metadata.title}</h1>
    <div class="metadata">
        <p><strong>Report ID:</strong> {artifact.metadata.report_id}</p>
        <p><strong>Generated At:</strong> {artifact.metadata.generated_at}</p>
        <p><strong>Version:</strong> {artifact.metadata.version.version_string}</p>
    </div>
    <hr/>
    {sections_html}
</body>
</html>"""

    def render_json(self, artifact: ReportArtifact) -> str:
        return json.dumps(artifact.model_dump(), indent=2)

    def render_csv(self, artifact: ReportArtifact) -> str:
        lines = ["Section,Title,Content"]
        for s in artifact.sections:
            safe_content = s.content.replace('"', '""')
            lines.append(f'"{s.section_id}","{s.title}","{safe_content}"')
        return "\n".join(lines)
