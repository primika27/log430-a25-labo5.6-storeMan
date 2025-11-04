"""
Order manager application
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import threading
from graphene import Schema
from stocks.schemas.query import Query
from flask import Flask, request, jsonify
from orders.controllers.order_controller import create_order, remove_order, get_order, get_report_highest_spending_users, get_report_best_selling_products, update_order
from orders.controllers.user_controller import create_user, remove_user, get_user
from stocks.controllers.product_controller import create_product, remove_product, get_product
from stocks.controllers.stock_controller import get_stock, populate_redis_on_startup, set_stock, get_stock_overview, update_stock
 
# TODO: utilisez pour la config à Jaeger
# from opentelemetry import trace
# from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
# from opentelemetry.sdk.resources import Resource
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import BatchSpanProcessor
# from opentelemetry.instrumentation.flask import FlaskInstrumentor
# from opentelemetry.instrumentation.requests import RequestsInstrumentor

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

app = Flask(__name__)

# TODO: Indiquez un nom pertinent à votre service
resource = Resource.create({
   "service.name": "nom-de-votre-service",
   "service.version": "1.0.0"
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Indiquez l'endpoint Jaeger (hostname dans Docker)
otlp_exporter = OTLPSpanExporter(
   endpoint="http://jaeger:4317",
   insecure=True
)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Automatic Flask instrumentation
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

# Ensuite, le code pour vos endpoints Flask, etc...

# Auto-populate Redis 5s after API startup (to give enough time for the DB to start up as well)
thread = threading.Timer(10.0, populate_redis_on_startup)
thread.daemon = True
thread.start()

@app.get('/health-check')
def health():
    """Return OK if app is up and running"""
    return jsonify({'status':'ok'})

# Write routes (Commands)
@app.post('/orders')
def post_orders():
    with tracer.start_as_current_span("post_orders"):
     return create_order(request)

@app.delete('/orders/<int:order_id>')
def delete_orders_id(order_id):
    """Delete an order with a given order_id"""
    with tracer.start_as_current_span("delete_orders_id"):
        return remove_order(order_id)

@app.post('/products')
def post_products():
    """Create a new product based on information on request body"""
    with tracer.start_as_current_span("post_products"):
        return create_product(request)

@app.delete('/products/<int:product_id>')
def delete_products_id(product_id):
    """Delete a product with a given product_id"""
    with tracer.start_as_current_span("delete_products_id"):
        return remove_product(product_id)

@app.post('/users')
def post_users():
    """Create a new user based on information on request body"""
    with tracer.start_as_current_span("post_users"):
        return create_user(request)

@app.delete('/users/<int:user_id>')
def delete_users_id(user_id):
    """Delete a user with a given user_id"""
    with tracer.start_as_current_span("delete_users_id"):
        return remove_user(user_id)

@app.post('/stocks')
def post_stocks():
    """Set product stock based on information on request body"""
    with tracer.start_as_current_span("post_stocks"):
        return set_stock(request)

@app.put('/stocks')
def put_stocks():
    """Check in/out product stock for given product_id and quantity"""
    with tracer.start_as_current_span("put_stocks"):
        return update_stock(request)

# Read routes (Queries) 
@app.get('/orders/<int:order_id>')
def get_order_id(order_id):
    """Get order with a given order_id"""
    return get_order(order_id)

@app.get('/products/<int:product_id>')
def get_product_id(product_id):
    """Get product with a given product_id"""
    return get_product(product_id)

@app.get('/users/<int:user_id>')
def get_user_id(user_id):
    """Get user with a given user_id"""
    return get_user(user_id)

@app.get('/stocks/<int:product_id>')
def get_stocks(product_id):
    """Get product stocks by product_id"""
    return get_stock(product_id)

@app.get('/orders/reports/highest-spenders')
def get_orders_highest_spending_users():
    """Get list of highest speding users, order by total expenditure"""
    rows = get_report_highest_spending_users()
    return jsonify(rows)

@app.get('/orders/reports/best-sellers')
def get_orders_report_best_selling_products():
    """Get list of best selling products, order by number of orders"""
    rows = get_report_best_selling_products()
    return jsonify(rows)

@app.get('/stocks/reports/overview-stocks')
def get_stocks_overview():
    """Get stocks for all products"""
    rows = get_stock_overview()
    return jsonify(rows)

# Endpoint that allows suppliers to check stock
@app.post('/stocks/graphql-query')
def graphql_supplier():
    data = request.get_json()
    schema = Schema(query=Query)
    result = schema.execute(data['query'], variables=data.get('variables'))
    return jsonify({
        'data': result.data,
        'errors': [str(e) for e in result.errors] if result.errors else None
    })

# Integration with payment service
@app.put('/orders')
def put_orders():
    """Update one or more order fields"""
    return update_order(request)

# Start Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
