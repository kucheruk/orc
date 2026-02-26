# Reviewing Database Migrations with Bugbot Rules

Bugbot rules automate code review by catching issues before they reach human reviewers. At Cursor, we use them for a variety of things, including catching database migration issues before they're merged.

## Review guidelines

Bugbot rules are markdown files that tell Bugbot exactly what to look for during code reviews. `.cursor/BUGBOT.md` files can be placed anywhere in the repository. Bugbot automatically includes the root file and traverses upward from changed files to find relevant context. When a PR opens, Bugbot reviews changes against these rules and comments on issues instantly.

## Database migrations get caught before merge

Database migrations can lock tables, cause downtime, or corrupt data if done incorrectly. Bugbot has eliminated most manual review work for DB migrations. By the time a human reviewer opens the PR, Bugbot has already flagged most things they would have caught.

Here's an example of a recent migration issue Bugbot caught:

![Bugbot catching a database migration issue](/docs-static/images/cookbook/bugbot-rules.png)

To catch Cursor infra-specific bugs, we've defined a set of review guidelines that Bugbot follows extra carefully when scanning code. Here's the rule we're using for catching the bug seen above:

```text
# Review Guidelines

## Database migrations

- When reviewing database migrations, ensure that they are backwards compatible. Specifically:

  - New tables, and new nullable or default columns on existing tables are OK.

  - New indices on existing tables (not brand new ones) must be created with keyword CONCURRENTLY. The statement should be isolated to its own migration file to avoid a prisma transaction error. You should warn on index creation and flag it for careful review.

  - Removing foreign keys and constraints is OK

  - Adding foreign keys is NOT OK

  - Removing indices is OK

  - Dropping columns is NOT OK. Instead, you should mark it as deprecated in the schema, and add a `@map` that corresponds to the original column name. For example, to deprecate the `hostname` column, you can change `hostname String?` to `hostname_DEPRECATED String? @map("hostname")`.

  - Renaming columns in the database, changing column types, or changing default values are NOT OK.

    - Exception: It is OK to increase the size of a VARCHAR column.

    - Exception: It is OK to make a non-null column nullable.

  - Dropping tables is NOT OK

- Enforce good guidelines when creating new tables and columns:

  - Prefer BIGINTEGER and BIGSERIAL over INTEGER and SERIAL, unless if you are absolutely sure that it will remain small (O(teams) or lower cardinality)

  - Using foreign keys for new tables is NOT OK. Handle this in the application layer instead.

  - Using cascading deletes for new tables is NOT OK, since a single delete may require the database to do an unbounded amount of work. Handle this in the application layer instead.

  - Prefer TEXT over VARCHAR

- Migrations and their corresponding schema.prisma changes should be isolated to their own PR when possible. We do not want unnecessary code changes that may need to be reverted to be coupled with migrations that have already been applied to production.

## Queries

- All new queries to maindb MUST use an index. It is NOT OK for the query to potentially execute a full table scan.

- All new queries to maindb MUST NOT do a `GROUP BY` or `JOIN`. Handle this in the application layer instead.

- Avoid Prisma's `skip` or SQL `OFFSET/LIMIT` on large tables - use cursor-based pagination instead by ordering on an indexed column
```

When an engineer creates an index without `CONCURRENTLY`, Bugbot flags it with a clear explanation and fix before any human opens the PR:

## Enforce team standards automatically

Bugbot rules work for any mechanical, rule-based review process. Some other examples we've seen:

- **Security reviews** block exposed secrets, unsafe API calls, or missing authentication checks.

- **Analytics standards** verify proper event tracking and naming conventions.

- **Code cleanliness** prevents untracked `TODO` comments:

```text
If any changed file contains /(?:^|\s)(TODO|FIXME)(?:\s*:|\s+)/, then:
- Add a non-blocking Bug titled "TODO/FIXME comment found"
- Body: "Replace TODO/FIXME with a tracked issue reference, e.g., `TODO(#1234): ...`, or remove it."
- If the TODO already references an issue pattern /#\d+|[A-Z]+-\d+/, mark the Bug as resolved automatically.
```

Bugbot handles mechanical review instantly and consistently. Engineers get immediate feedback, dangerous changes are caught before merge, and human reviewers focus on architecture and logic instead of style guides.

Create `.cursor/BUGBOT.md` in your repo with your team's rules. Bugbot will automatically enforce them on every PR. [Read more about Bugbot rules](https://cursor.com/docs/bugbot.md).


---

## Sitemap

[Overview of all docs pages](/llms.txt)
