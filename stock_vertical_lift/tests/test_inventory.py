# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _

from .common import VerticalLiftCase


class TestInventory(VerticalLiftCase):
    def test_switch_inventory(self):
        self.shuttle.switch_inventory()
        self.assertEqual(self.shuttle.mode, "inventory")
        self.assertEqual(
            self.shuttle._operation_for_mode().current_inventory_line_id,
            self.env["stock.inventory.line"].browse(),
        )

    def test_inventory_action_open_screen(self):
        self.shuttle.switch_inventory()
        action = self.shuttle.action_open_screen()
        operation = self.shuttle._operation_for_mode()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "vertical.lift.operation.inventory")
        self.assertEqual(action["res_id"], operation.id)

    def test_inventory_count_ops(self):
        self._update_qty_in_location(self.location_1a_x1y1, self.product_socks, 10)
        self._update_qty_in_location(self.location_1a_x2y1, self.product_recovery, 10)
        self._create_inventory(
            [
                (self.location_1a_x1y1, self.product_socks),
                (self.location_1a_x2y1, self.product_recovery),
            ]
        )
        self._update_qty_in_location(self.location_2a_x1y1, self.product_socks, 10)
        self._create_inventory([(self.location_2a_x1y1, self.product_socks)])

        operation = self._open_screen("inventory")
        self.assertEqual(operation.number_of_ops, 2)
        self.assertEqual(operation.number_of_ops_all, 3)

    def test_process_current_inventory(self):
        self._update_qty_in_location(self.location_1a_x1y1, self.product_socks, 10)
        inventory = self._create_inventory(
            [(self.location_1a_x1y1, self.product_socks)]
        )
        operation = self._open_screen("inventory")
        self.assertEqual(operation.state, "quantity")
        self.assertEqual(operation.current_inventory_line_id, inventory.line_ids)
        # test the happy path, quantity is correct
        operation.quantity_input = 10.0
        result = operation.button_save()

        # state is reset
        # noop because we have no further lines
        self.assertEqual(operation.state, "noop")
        self.assertFalse(operation.current_inventory_line_id)
        self.assertTrue(inventory.line_ids.vertical_lift_done)
        self.assertEqual(inventory.state, "done")
        expected_result = {
            "effect": {
                "fadeout": "slow",
                "message": _("Congrats, you cleared the queue!"),
                "img_url": "/web/static/src/img/smile.svg",
                "type": "rainbow_man",
            }
        }
        self.assertEqual(result, expected_result)

    def test_wrong_quantity(self):
        self._update_qty_in_location(self.location_1a_x1y1, self.product_socks, 10)
        inventory = self._create_inventory(
            [(self.location_1a_x1y1, self.product_socks)]
        )
        operation = self._open_screen("inventory")
        line = operation.current_inventory_line_id
        self.assertEqual(line, inventory.line_ids)

        operation.quantity_input = 12.0
        operation.button_save()
        self.assertEqual(operation.last_quantity_input, 12.0)
        self.assertEqual(operation.quantity_input, 0.0)
        self.assertEqual(operation.state, "confirm_wrong_quantity")
        self.assertEqual(operation.current_inventory_line_id, line)

        # entering the same quantity a second time validates
        operation.quantity_input = 12.0
        operation.button_save()
        self.assertFalse(operation.current_inventory_line_id)

        self.assertTrue(inventory.line_ids.vertical_lift_done)
        self.assertEqual(inventory.state, "done")

    def test_inventory_next_line(self):
        self._update_qty_in_location(self.location_1a_x1y1, self.product_socks, 10)
        self._update_qty_in_location(self.location_1a_x2y1, self.product_recovery, 10)
        inventory = self._create_inventory(
            [
                (self.location_1a_x1y1, self.product_socks),
                (self.location_1a_x2y1, self.product_recovery),
            ]
        )
        inventory_lines = inventory.line_ids
        operation = self._open_screen("inventory")
        operation.quantity_input = 10.0
        line1 = operation.current_inventory_line_id
        result = operation.button_save()
        self.assertFalse(result)  # no rainbow man

        # go to next line
        remaining_line = inventory_lines - line1
        self.assertEqual(operation.state, "quantity")
        self.assertEqual(operation.current_inventory_line_id, remaining_line)
        self.assertEqual(operation.last_quantity_input, 0.0)
        self.assertEqual(operation.quantity_input, 0.0)
