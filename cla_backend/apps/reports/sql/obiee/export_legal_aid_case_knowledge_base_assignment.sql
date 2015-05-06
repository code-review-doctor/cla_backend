COPY (SELECT
id,
created,
modified,
case_id,
alternative_help_article_id,
assigned_by_id
FROM legalaid_caseknowledgebaseassignment
WHERE (modified >= %(from_date)s::timestamp AND modified <= %(to_date)s::timestamp)
OR (created >= %(from_date)s::timestamp AND created <= %(to_date)s::timestamp))
TO STDOUT CSV HEADER;
