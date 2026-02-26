# Data Science

Cursor provides integrated tooling for data science development through reproducible environments, notebook
support, and AI-powered code assistance. This guide covers essential setup patterns for Python, R, and SQL
workflows.

## Notebook development

For full notebook support, download the Jupyter (id: ms-toolsai.jupyter) extension, published by ms-toolsai.

Cursor supports both `.ipynb` and `.py` files with integrated cell execution. Tab, Inline Edit, and Agents
work within notebooks, just as they do in other code files.

Key capabilities:

- **Inline cell execution** runs code directly within the editor interface
- **Tab, Inline Edit, and Agent** all understand data science libraries including pandas, NumPy, scikit-learn, and SQL magic commands

## Database integration

Databases can be integrated with Cursor through two main mechanisms: MCP servers and Extensions.

- **MCP Servers** let your Agents connect with your databases
- **Extensions** integrate your broader editor with your databases

### Via MCP

MCP servers allow your agent to make queries directly against your database. This allows your agent to choose to query your database, write the appropriate query, run the command and analyze outputs, all as part of an ongoing task.

For example, you can connect a Postgres database to your Cursor instance by adding the following [MCP config](https://github.com/modelcontextprotocol/servers-archived/tree/main/src/postgres) to Cursor:

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://localhost/mydb"
      ]
    }
  }
}
```

For more on MCP, see our [MCP documentation](https://cursor.com/docs/context/mcp.md).

[Media](/docs-static/images/guides/advanced/datascience/postgres-mcp.mp4)

Your browser does not support the video tag.

### Via Extensions

Install database-specific extensions (PostgreSQL, BigQuery, SQLite, Snowflake) to execute queries directly from the editor. This eliminates context switching between tools and enables AI assistance for query optimization.

```sql
-- Cursor provides suggestions for indexes, window functions, and query optimization
SELECT
    user_id,
    event_type,
    COUNT(*) as event_count,
    RANK() OVER (PARTITION BY user_id ORDER BY COUNT(*) DESC) as frequency_rank
FROM events
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY user_id, event_type;
```

Use Agents to analyze slow queries, suggest performance improvements, or generate visualization code for query results. Cursor understands SQL context and can recommend appropriate chart types based on your data structure.

![Snowflake Extension](/docs-static/images/guides/advanced/datascience/snowflake-extension.png)

## Data visualization

Cursor's AI assistance extends to data visualization libraries including Matplotlib, Plotly, and Seaborn. The agent can generate code for data visualization, helping you quickly and easily explore data, while creating a replicable and shareable artifact.

```python
import plotly.express as px
import pandas as pd

# AI suggests relevant plot types based on data columns
df = pd.read_csv('sales_data.csv')
fig = px.scatter(df, x='advertising_spend', y='revenue',
                 color='region', size='customer_count',
                 title='Revenue vs Advertising Spend by Region')
fig.show()
```

[Media](/docs-static/images/guides/advanced/datascience/datascience-visualization.mp4)

Your browser does not support the video tag.

## Frequently asked questions

**Can I use existing Jupyter notebooks?**
Yes, Cursor opens `.ipynb` files with full cell execution and AI completion support.

**How do I handle large datasets that don't fit in memory?**
Use distributed computing libraries like Dask or connect to Spark clusters through Remote-SSH connections to larger machines.

**Does Cursor support R and SQL files?**
Yes, Cursor provides AI assistance and syntax highlighting for R scripts (`.R`) and SQL files (`.sql`).

**What's the recommended way to share development environments?**
Commit the `.devcontainer` folder to version control. Team members can rebuild the environment automatically when opening the project.

**How do I debug data processing pipelines?**
Use Cursor's integrated debugger with breakpoints in Python scripts, or leverage Agent to analyze and explain complex data transformations step by step.

## Environment reproducibility

### Development containers

Development containers help you ensure consistent runtimes and dependencies across team members and deployment environments. They can eliminate environment-specific bugs and reduce onboarding time for new team members.

To use a development container, start by creating a `.devcontainer` folder in your repository root. Next, create a `devcontainer.json`, `Dockerfile`, and `requirements.txt` file.

```json
{
  "name": "ds-env",
  "build": { "dockerfile": "Dockerfile" },
  "features": {
    "ghcr.io/devcontainers/features/python:1": { "version": "3.11" }
  },
  "postCreateCommand": "pip install -r requirements.txt"
}
```

```dockerfile
# .devcontainer/Dockerfile
FROM mcr.microsoft.com/devcontainers/python:3.11
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt
```

```txt
# requirements.txt
pandas==2.3.0
numpy
# add other dependencies you need for your project
```

Cursor will automatically detect the devcontainer and prompt you to reopen your project within a container. Alternatively, you can manually reopen in a container using the Command Palette (Cmd+Shift+P) and searching for `Reopen in Container`.

Development containers provide several advantages:

- **Dependency isolation** prevents conflicts between projects
- **Reproducible builds** ensure consistent behavior across development and production environments
- **Simplified onboarding** allows new team members to start immediately without manual setup

### Remote development with SSH

When your analysis requires additional compute resources, GPUs, or access to private datasets, connect to remote machines while maintaining your local development environment.

1. Provision a cloud instance or access an on-premises server with required resources
2. Clone your repository to the remote machine, including the `.devcontainer` configuration
3. Connect through Cursor: Cmd+Shift+P → "Remote-SSH: Connect to Host"

This approach maintains consistent tooling while scaling compute resources as needed. The same development container configuration works across local and remote environments.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
