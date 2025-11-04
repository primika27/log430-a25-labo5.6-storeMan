"""
Order controller
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""

from logger import Logger
from flask import jsonify
from db import get_redis_conn
from orders.commands.write_order import add_order, delete_order, modify_order
from orders.queries.read_order import get_order_by_id, get_best_selling_products, get_highest_spending_users

logger = Logger.get_instance("order_controller")

def create_order(request):
    """Create order, use WriteOrder model"""
    payload = request.get_json() or {}
    user_id = payload.get('user_id')
    items = payload.get('items', [])
    try:
        order_id = add_order(user_id, items)
        return jsonify({'order_id': order_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
def update_order(request, order_id):
    """Update order with given order_id, use WriteOrder model"""
    payload = request.get_json() or {}
    is_paid = payload.get('is_paid')
    user_id = payload.get('user_id')
    total_amount = payload.get('total_amount')
    items = payload.get('items')
    
    logger.debug(f"Mettre à jour la commande {order_id}")

    try:
        # update MySQL
        status = modify_order(order_id, is_paid=is_paid, user_id=user_id, total_amount=total_amount, items=items)
        
        if not status:
            return jsonify({'error': 'Order not found or update failed'}), 404
        
        # update Redis
        r = get_redis_conn()
        order = r.hgetall(f"order:{order_id}")
        
        if order:
            # Update fields in Redis if they were provided
            if is_paid is not None:
                order['is_paid'] = str(is_paid)
            if user_id is not None:
                order['user_id'] = str(user_id)
            if total_amount is not None:
                order['total_amount'] = str(total_amount)
            if items is not None:
                import json
                order['items'] = json.dumps(items) if not isinstance(items, str) else items
            
            r.hset(f"order:{order_id}", mapping=order)

        # response
        logger.debug(f"Commande {order_id} mise à jour avec succès")
        return jsonify({'updated': True, 'order_id': order_id}), 200
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de la commande {order_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

def remove_order(order_id):
    """Delete order, use WriteOrder model"""
    try:
        deleted = delete_order(order_id)
        if deleted:
            return jsonify({'deleted': True})
        return jsonify({'deleted': False}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_order(order_id):
    """Create order, use ReadOrder model"""
    try:
        order = get_order_by_id(order_id)
        return jsonify(order), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
def get_report_highest_spending_users():
    """Get orders report: highest spending users"""
    return get_highest_spending_users()

def get_report_best_selling_products():
    """Get orders report: best selling products"""
    return get_best_selling_products()