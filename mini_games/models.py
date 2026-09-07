from extensions import db  # Or wherever your `db` instance is imported from in your project

class PuzzleScenario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(20), default="medium")  # easy, medium, hard
    hand_cards = db.Column(db.Text, nullable=False)  # JSON or comma-separated card list
    board_state = db.Column(db.Text, nullable=True)  # Cards already in play
    solution_criteria = db.Column(db.Text, nullable=False)  # Dependency rules / correct sequence
    description = db.Column(db.Text, nullable=True)