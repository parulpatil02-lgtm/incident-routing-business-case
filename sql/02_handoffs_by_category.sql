-- Where are the hand-offs concentrated? Total hand-offs per category, using
-- the first category recorded on each incident. Builds on 01_handoffs.sql.

WITH known AS (
    SELECT
        number,
        assignment_group,
        LAG(assignment_group) OVER (
            PARTITION BY number ORDER BY sys_mod_count, rowid
        ) AS previous_group
    FROM events
    WHERE assignment_group <> '?'
),
per_incident AS (
    SELECT
        number,
        SUM(CASE WHEN previous_group IS NOT NULL
                  AND assignment_group <> previous_group THEN 1 ELSE 0 END) AS group_changes
    FROM known
    GROUP BY number
),
first_category AS (
    SELECT number, category
    FROM (
        SELECT
            number,
            category,
            ROW_NUMBER() OVER (PARTITION BY number ORDER BY sys_mod_count, rowid) AS rn
        FROM events
        WHERE category <> '?'
    )
    WHERE rn = 1
)
SELECT
    c.category,
    COUNT(*)                AS incidents,
    SUM(p.group_changes)    AS handoffs,
    ROUND(1.0 * SUM(CASE WHEN p.group_changes > 0 THEN 1 ELSE 0 END) / COUNT(*), 4) AS share_that_changed_hands
FROM per_incident AS p
JOIN first_category AS c ON c.number = p.number
GROUP BY c.category
ORDER BY handoffs DESC;
