import os
from flask import Flask, render_template
from config import Config
from database import db, init_db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize directory directories
    config_class.init_app(app)
    
    # Initialize Database
    init_db(app)
    
    # Register blueprints
    from routes import routes_bp
    from api import api_bp
    
    app.register_blueprint(routes_bp)
    app.register_blueprint(api_bp)
    
    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
        
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500
        
    # Inject user/admin details globally in templates
    @app.context_processor
    def inject_now():
        from datetime import datetime, timezone
        return {'now': datetime.now(timezone.utc)}
        
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # In production, run with gunicorn, otherwise debug server
    app.run(host='0.0.0.0', port=port, debug=current_app.config['DEBUG'] if 'current_app' in locals() else True)
