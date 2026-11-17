CREATE VIEW attendance_report AS
SELECT e.student_id, e.region, a.absent_days
FROM enrollment e JOIN attendance_summary a ON e.student_id = a.student_id;

CREATE VIEW review_candidates AS
SELECT a.student_id, a.region, a.absent_days, b.incidents
FROM attendance_report a LEFT JOIN behavior_summary b ON a.student_id = b.student_id;

CREATE VIEW regional_review AS
SELECT e.region, COUNT(r.student_id) AS review_records
FROM review_candidates r JOIN enrollment e ON r.student_id = e.student_id
GROUP BY e.region;
