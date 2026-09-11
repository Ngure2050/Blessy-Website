from flask import Flask, render_template, request

app = Flask(__name__)


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/order")
def order():
    product = request.args.get("product", "your selected product")
    return render_template("order.html", product=product)


if __name__ == "__main__":
    app.run(debug=True)
