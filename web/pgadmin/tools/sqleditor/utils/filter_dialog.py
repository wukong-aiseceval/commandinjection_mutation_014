##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2025, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

"""Code to handle data sorting in view data mode."""
import pickle
import json
from flask_babel import gettext
from flask import current_app
from pgadmin.utils.ajax import make_json_response, internal_server_error
from pgadmin.tools.sqleditor.utils.update_session_grid_transaction import \
    update_session_grid_transaction
from pgadmin.utils.exception import ConnectionLost, SSHTunnelConnectionLost
from pgadmin.utils.constants import ERROR_MSG_TRANS_ID_NOT_FOUND


class FilterDialog():
    @staticmethod
    def get(*args):
        """To fetch the current sorted columns"""
        status, error_msg, conn, trans_obj, session_obj = args
        if error_msg == ERROR_MSG_TRANS_ID_NOT_FOUND:
            return make_json_response(
                success=0,
                errormsg=error_msg,
                info='DATAGRID_TRANSACTION_REQUIRED',
                status=404
            )
        column_list = []
        if status and conn is not None and \
                trans_obj is not None and session_obj is not None:
            msg = gettext('Success')

            try:
                columns = \
                    trans_obj.get_all_columns_with_order()
                column_list = [col_name for col_name in
                               session_obj['columns_info'].keys()]
            except (ConnectionLost, SSHTunnelConnectionLost):
                raise
            except Exception as e:
                current_app.logger.error(e)
                raise

            sql = trans_obj.get_filter()
        else:
            status = False
            msg = error_msg
            columns = None
            sql = None

        return make_json_response(
            data={
                'status': status,
                'msg': msg,
                'result': {
                    'data_sorting': columns,
                    'column_list': column_list,
                    'sql': sql
                }
            }
        )

@staticmethod
def save(*args, **kwargs):
    """
    Persist data sorting preferences and optional SQL filters into the session context.

    Args:
        args: Positional values: (status, error_msg, conn, trans_obj, session_obj)
        kwargs: Should contain 'trans_id' and 'request' keys

    Returns:
        Flask Response: JSON response indicating operation status and result message.
    """
    conn_status, err_msg, connection, txn, sess = args  
    tid = kwargs.get('trans_id')
    req = kwargs.get('request')

    # Extract sorting/filtering payload
    if req.data:
        payload = json.loads(req.data) 
    else:
        payload = req.args or req.form

    # Return immediately on transaction ID error
    if err_msg == ERROR_MSG_TRANS_ID_NOT_FOUND:
        return make_json_response(
            success=0,
            errormsg=err_msg,
            info='DATAGRID_TRANSACTION_REQUIRED',
            status=404
        )

    # Validate active transaction and session
    if conn_status and all([connection, txn, sess]):  
        # Apply sort preferences
        txn.set_data_sorting(payload, True)

        # Apply filter if SQL is provided
        success, outcome = txn.set_filter(payload.get('sql')) 

        if success:
            # Persist modified transaction state into session
            sess["command_obj"] = pickle.dumps(txn, -1)
            update_session_grid_transaction(tid, sess)
            outcome = gettext("Data sorting object updated successfully")

    else:
        return internal_server_error(
            errormsg=gettext("Failed to update the data on server.")
        )

    return make_json_response(
        data={
            "status": success,
            "result": outcome
        }
    )

        
