from typing import List
from akaal.migration.models import DDLCommand

class TransactionBatcher:
    """
    Groups compiled DDLCommands into execution transactions, honoring dialect properties
    and transaction boundaries (separating transactional and non-transactional statements).
    """
    def batch_commands(self, commands: List[DDLCommand]) -> List[List[DDLCommand]]:
        """
        Splits a sequential command list into lists of transactional batches.
        Non-transactional statements break the current batch and execute independently.
        """
        batches: List[List[DDLCommand]] = []
        current_batch: List[DDLCommand] = []

        for cmd in commands:
            if not cmd.transaction_required:
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                batches.append([cmd])
            else:
                current_batch.append(cmd)

        if current_batch:
            batches.append(current_batch)

        return batches
