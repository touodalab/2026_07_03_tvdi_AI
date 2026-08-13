SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'salary_data2';

SELECT DISTINCT "City" AS city
FROM public.salary_data2
WHERE "City" IS NOT NULL
ORDER BY city;