ALTER TABLE Movement
  ADD COLUMN recurrent_movement_id INTEGER
  REFERENCES RecurrentMovement(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_movement_recurrent
  ON Movement(recurrent_movement_id);
