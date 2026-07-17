import unittest
from akaal.core.conversion.api.service import ConversionRequest
from akaal.core.conversion.api.aoir import RoutineKind, VolatilitySemantics
from akaal.core.conversion.api.models import ConversionContext, DbVersion
from akaal.core.models.enums import SystemType
from akaal.core.conversion.internal.parser.routine_parser import RoutineParser
from akaal.core.conversion.internal.routine.service_impl import RoutineConversionService
from akaal.core.conversion.internal.bootstrap import Bootstrap

class TestRoutineCompiler(unittest.TestCase):
    def test_parse_procedure_and_versioning(self):
        source = """
        CREATE OR REPLACE PROCEDURE log_message(
            p_msg IN VARCHAR2,
            p_level IN NUMBER DEFAULT 1
        ) IS
            v_temp VARCHAR2(50) := 'TEMP';
        BEGIN
            DBMS_OUTPUT.PUT_LINE(p_msg);
        END;
        """
        parser = RoutineParser(source, source_dialect="oracle", target_dialect="postgresql")
        aoir = parser.parse_routine()

        self.assertEqual(aoir.name, "log_message")
        self.assertEqual(aoir.kind, RoutineKind.PROCEDURE)
        self.assertEqual(aoir.aoir_version, "1.0.0")
        self.assertEqual(aoir.source_dialect, "oracle")
        self.assertEqual(aoir.target_dialect, "postgresql")
        self.assertEqual(aoir.routine_type, "PROCEDURE")
        self.assertEqual(len(aoir.parameters), 2)
        self.assertEqual(aoir.parameters[0].name, "p_msg")
        self.assertEqual(aoir.parameters[1].default_expression, "1")
        self.assertEqual(len(aoir.local_variables), 1)
        self.assertEqual(aoir.local_variables[0].name, "v_temp")

    def test_parse_function_and_versioning(self):
        source = """
        CREATE OR REPLACE FUNCTION double_val(
            p_val IN NUMBER
        ) RETURN NUMBER IS
        BEGIN
            RETURN p_val * 2;
        END;
        """
        parser = RoutineParser(source, source_dialect="oracle", target_dialect="postgresql")
        aoir = parser.parse_routine()

        self.assertEqual(aoir.name, "double_val")
        self.assertEqual(aoir.kind, RoutineKind.FUNCTION)
        self.assertIsNotNone(aoir.return_spec)
        self.assertEqual(aoir.return_spec.data_type, "NUMBER")
        self.assertEqual(aoir.routine_type, "FUNCTION")

    def test_conversion_service_e2e(self):
        source = """
        CREATE OR REPLACE FUNCTION test_fn(x NUMBER) RETURN NUMBER IS
        BEGIN
            RETURN x;
        END;
        """
        from akaal.core.conversion.api.models import ConversionPolicy
        ctx = ConversionContext(
            source_vendor="oracle",
            source_version=DbVersion.parse("19c"),
            target_vendor="postgres",
            target_version=DbVersion.parse("15"),
            policy=ConversionPolicy()
        )
        req = ConversionRequest(
            source_ddl=source,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            context=ctx
        )
        service = Bootstrap.initialize_function_service()
        res = service.convert_function(req)

        self.assertTrue(res.success)
        self.assertIn("CREATE OR REPLACE FUNCTION test_fn", res.target_sql)
        self.assertIn("RETURNS NUMERIC", res.target_sql)
        self.assertIn("LANGUAGE plpgsql", res.target_sql)
