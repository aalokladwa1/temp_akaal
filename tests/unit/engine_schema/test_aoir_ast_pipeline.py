"""
tests.unit.engine_schema.test_aoir_ast_pipeline
==============================================
Unit tests proving procedural parsing, AST nodes, transformations, and PL/pgSQL emission (SCH-042 to SCH-052).
"""

import pytest

from akaalEngine.schema.models.programmables import ParameterMode, RoutineKind
from akaalEngine.schema.procedural.ast_nodes import (
    AssignmentStatement,
    BlockNode,
    CursorDefinition,
    ExceptionHandler,
    ForLoopStatement,
    IfStatement,
    RaiseStatement,
    RoutineAST,
)
from akaalEngine.schema.procedural.emitters.plpgsql import PLpgSQLEmitter
from akaalEngine.schema.procedural.parsers.plsql import PLSQLParser
from akaalEngine.schema.procedural.parsers.tsql import TSQLParser


def test_oracle_plsql_procedure_parsing_and_emission():
    oracle_sql = """
    CREATE OR REPLACE PROCEDURE update_customer_balance(
        p_cust_id IN NUMBER,
        p_amount IN NUMBER,
        p_status OUT VARCHAR2
    )
    IS
        v_current_bal NUMBER(12,2) := 0;
        CURSOR c_orders IS SELECT id, total FROM orders WHERE customer_id = p_cust_id;
    BEGIN
        SELECT balance INTO v_current_bal FROM customers WHERE id = p_cust_id;
        IF v_current_bal + p_amount < 0 THEN
            p_status := 'INSUFFICIENT_FUNDS';
            RAISE_APPLICATION_ERROR(-20001, 'Balance cannot be negative');
        ELSE
            UPDATE customers SET balance = v_current_bal + p_amount WHERE id = p_cust_id;
            p_status := 'SUCCESS';
        END IF;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            p_status := 'NOT_FOUND';
        WHEN OTHERS THEN
            p_status := 'ERROR';
    END update_customer_balance;
    """

    parser = PLSQLParser(oracle_sql)
    ast = parser.parse()

    assert ast.name == "update_customer_balance"
    assert ast.routine_type == RoutineKind.PROCEDURE
    assert len(ast.parameters) == 3
    assert ast.parameters[0].name == "p_cust_id"
    assert ast.parameters[2].mode == ParameterMode.OUT

    # Verify declarations
    assert len(ast.body.declarations) == 2
    assert any(isinstance(d, CursorDefinition) for d in ast.body.declarations)

    # Verify exception handlers
    assert len(ast.body.exception_handlers) == 2

    # Transpile to PostgreSQL PL/pgSQL
    res = PLpgSQLEmitter.emit_routine(ast, schema_name="sales")
    assert res.target_engine == "POSTGRESQL"
    assert 'CREATE OR REPLACE PROCEDURE "sales"."update_customer_balance"' in res.target_sql
    assert "DECLARE" in res.target_sql
    assert "CURSOR FOR" in res.target_sql
    assert "EXCEPTION" in res.target_sql
    assert "WHEN NO_DATA_FOUND THEN" in res.target_sql


def test_oracle_pragma_autonomous_transaction():
    oracle_sql = """
    CREATE OR REPLACE PROCEDURE log_audit_event(p_event VARCHAR2)
    IS
        PRAGMA AUTONOMOUS_TRANSACTION;
    BEGIN
        INSERT INTO audit_log (event_name) VALUES (p_event);
        COMMIT;
    END;
    """
    parser = PLSQLParser(oracle_sql)
    ast = parser.parse()

    assert ast.is_autonomous is True

    res = PLpgSQLEmitter.emit_routine(ast, schema_name="audit")
    assert any(d.category == "AUTONOMOUS_TRANSACTION" for d in res.diagnostics)


def test_tsql_procedure_parsing():
    tsql_sql = """
    CREATE PROCEDURE sp_process_order
        @order_id INT,
        @result VARCHAR(50) OUTPUT
    AS
    BEGIN
        SET NOCOUNT ON;
        DECLARE @current_status VARCHAR(20) = 'PENDING';
        BEGIN TRY
            IF @current_status = 'PENDING'
            BEGIN
                UPDATE orders SET status = 'PROCESSING' WHERE id = @order_id;
                SET @result = 'OK';
            END
            ELSE
            BEGIN
                SET @result = 'SKIP';
            END
        END TRY
        BEGIN CATCH
            SET @result = 'FAILED';
        END CATCH
    END
    """
    parser = TSQLParser(tsql_sql)
    ast = parser.parse()

    assert ast.name == "sp_process_order"
    assert len(ast.parameters) == 2
    assert ast.parameters[1].mode == ParameterMode.OUT
    assert len(ast.body.declarations) == 1
    assert len(ast.body.exception_handlers) == 1
