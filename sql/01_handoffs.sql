-- How often do incidents change hands between teams?
--
-- The raw log has one row per ticket update. For each incident, keep the rows
-- where a group was assigned, compare each group with the previous one (LAG),
-- and count the changes. Works on a table named `events` with the columns
-- number, sys_mod_count, assignment_group ('?' means "not assigned yet").

WITH known AS (
    SELECT
        number,
        assignment_group,
        LAG(assignment_group) OVER (
            PARTITION BY number
            ORDER BY sys_mod_count, rowid
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
)
SELECT
    COUNT(*)                                        AS incidents_with_a_group,
    SUM(group_changes)                              AS total_handoffs,
    SUM(CASE WHEN group_changes > 0 THEN 1 ELSE 0 END) AS incidents_that_changed_hands,
    ROUND(1.0 * SUM(CASE WHEN group_changes > 0 THEN 1 ELSE 0 END) / COUNT(*), 4) AS share_that_changed_hands
FROM per_incident;
