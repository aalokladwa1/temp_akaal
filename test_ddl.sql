CREATE TABLE employees (
    emp_id NUMBER(10) PRIMARY KEY,
    first_name VARCHAR2(50),
    last_name VARCHAR2(50) NOT NULL,
    hire_date DATE,
    salary NUMBER(15, 2),
    resume CLOB
);

CREATE TABLE locations (
    loc_id NUMBER(10),
    geom SDO_GEOMETRY,
    metadata JSON
);
