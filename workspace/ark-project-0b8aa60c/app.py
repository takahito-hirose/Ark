from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    """
    The route to render the index template.
    
    Returns:
        render_template: The rendered index template.
    💋
    """
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)