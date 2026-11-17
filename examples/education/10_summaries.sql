CREATE VIEW attendance_summary AS
SELECT student_id, SUM(absent_days) AS absent_days
FROM attendance_events GROUP BY student_id;

CREATE VIEW behavior_summary AS
SELECT student_id, SUM(incident_count) AS incidents
FROM behavior_events GROUP BY student_id;
