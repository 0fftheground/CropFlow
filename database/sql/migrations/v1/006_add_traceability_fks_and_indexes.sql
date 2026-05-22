-- V1 Migration 006
-- Purpose:
--   Add deferred foreign keys, indexes, comments, and updated_at triggers.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_calendar_item_generated_task'
  ) THEN
    ALTER TABLE cf_calendar_item
      ADD CONSTRAINT fk_cf_calendar_item_generated_task
      FOREIGN KEY (generated_task_id) REFERENCES cf_farming_task(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_task_intent_converted_task'
  ) THEN
    ALTER TABLE cf_task_intent
      ADD CONSTRAINT fk_cf_task_intent_converted_task
      FOREIGN KEY (converted_task_id) REFERENCES cf_farming_task(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_calendar_item_parent_task'
  ) THEN
    ALTER TABLE cf_calendar_item
      ADD CONSTRAINT fk_cf_calendar_item_parent_task
      FOREIGN KEY (parent_task_id) REFERENCES cf_farming_task(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_task_intent_parent_task'
  ) THEN
    ALTER TABLE cf_task_intent
      ADD CONSTRAINT fk_cf_task_intent_parent_task
      FOREIGN KEY (parent_task_id) REFERENCES cf_farming_task(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_farming_task_parent_task'
  ) THEN
    ALTER TABLE cf_farming_task
      ADD CONSTRAINT fk_cf_farming_task_parent_task
      FOREIGN KEY (parent_task_id) REFERENCES cf_farming_task(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_calendar_item_source_execution'
  ) THEN
    ALTER TABLE cf_calendar_item
      ADD CONSTRAINT fk_cf_calendar_item_source_execution
      FOREIGN KEY (source_execution_id) REFERENCES cf_execution(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_calendar_item_source_execution_record'
  ) THEN
    ALTER TABLE cf_calendar_item
      ADD CONSTRAINT fk_cf_calendar_item_source_execution_record
      FOREIGN KEY (source_execution_record_id) REFERENCES cf_execution_record(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_task_intent_source_execution'
  ) THEN
    ALTER TABLE cf_task_intent
      ADD CONSTRAINT fk_cf_task_intent_source_execution
      FOREIGN KEY (source_execution_id) REFERENCES cf_execution(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_task_intent_source_execution_record'
  ) THEN
    ALTER TABLE cf_task_intent
      ADD CONSTRAINT fk_cf_task_intent_source_execution_record
      FOREIGN KEY (source_execution_record_id) REFERENCES cf_execution_record(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_farming_task_source_execution'
  ) THEN
    ALTER TABLE cf_farming_task
      ADD CONSTRAINT fk_cf_farming_task_source_execution
      FOREIGN KEY (source_execution_id) REFERENCES cf_execution(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_cf_farming_task_source_execution_record'
  ) THEN
    ALTER TABLE cf_farming_task
      ADD CONSTRAINT fk_cf_farming_task_source_execution_record
      FOREIGN KEY (source_execution_record_id) REFERENCES cf_execution_record(id) ON DELETE SET NULL;
  END IF;
END;
$$;

COMMENT ON TABLE cf_farm IS
  'Farm master data.';
COMMENT ON TABLE cf_field IS
  'Field master data.';
COMMENT ON TABLE cf_farm_field_relation IS
  'Relation between farms and fields.';
COMMENT ON TABLE cf_code_dict IS
  'Shared code dictionary table used by plan and variety reference fields.';
COMMENT ON TABLE cf_user IS
  'Minimal user table used by review and notification modules.';
COMMENT ON TABLE cf_user_account IS
  'User account and authentication profile table.';
COMMENT ON TABLE cf_rice_variety IS
  'Rice variety reference table.';
COMMENT ON TABLE cf_planting_plan IS
  'Top-level planting plan aggregate root for MVP orchestration.';
COMMENT ON TABLE cf_planting_plan_field_relation IS
  'Relation between a planting plan and its fields.';
COMMENT ON TABLE cf_event_record IS
  'Normalized inbound and internal event log consumed by orchestrators.';
COMMENT ON TABLE cf_stage_prediction_snapshot IS
  'Stage prediction snapshot emitted by stage prediction algorithms.';
COMMENT ON TABLE cf_crop_stage_state IS
  'Current crop stage state for a planting plan.';
COMMENT ON TABLE cf_crop_thermal_time_state IS
  'Accumulated thermal time state for a planting plan.';
COMMENT ON TABLE cf_calendar_item IS
  'Preparatory calendar item used for future survey, evaluation, or stage-driven task generation.';
COMMENT ON TABLE cf_task_intent IS
  'Runtime task suggestion awaiting review or later conversion into a formal farming task.';
COMMENT ON TABLE cf_review_request IS
  'Human review work item created from task intents, feedback, or runtime exceptions.';
COMMENT ON TABLE cf_farming_task IS
  'Formal executable farming task and entry object for the execution module.';
COMMENT ON TABLE cf_operation_plan IS
  'Concrete operation plan or prescription attached to a formal farming task.';
COMMENT ON TABLE cf_execution IS
  'Execution instance of a farming task.';
COMMENT ON TABLE cf_execution_record IS
  'Execution or survey result record captured during an execution.';
COMMENT ON TABLE cf_evaluation IS
  'Evaluation result derived from execution outcome.';
COMMENT ON TABLE cf_feedback IS
  'Operational feedback derived from evaluation or runtime signals.';
COMMENT ON TABLE cf_system_notification IS
  'User-facing notification generated by review, task, or execution flows.';

COMMENT ON COLUMN cf_user.status IS
  'Suggested values: active, disabled.';
COMMENT ON COLUMN cf_user_account.account_type IS
  'Suggested values: password, sso, external.';
COMMENT ON COLUMN cf_user_account.status IS
  'Suggested values: active, locked, disabled.';
COMMENT ON COLUMN cf_planting_plan.status IS
  'Suggested values: draft, active, completed, cancelled.';
COMMENT ON COLUMN cf_event_record.event_category IS
  'Suggested values: input, domain.';
COMMENT ON COLUMN cf_event_record.event_source IS
  'Suggested values: user, job, external, module.';
COMMENT ON COLUMN cf_event_record.payload IS
  'Normalized event payload consumed by orchestrators and handlers.';
COMMENT ON COLUMN cf_event_record.processing_status IS
  'Suggested values: received, processing, processed, failed, ignored.';
COMMENT ON COLUMN cf_stage_prediction_snapshot.input_payload IS
  'Input snapshot sent to the stage prediction algorithm.';
COMMENT ON COLUMN cf_stage_prediction_snapshot.stage_timeline IS
  'Predicted stage timeline returned by the stage prediction algorithm.';
COMMENT ON COLUMN cf_stage_prediction_snapshot.thermal_thresholds IS
  'Thermal threshold snapshot used by stage prediction and later audits.';
COMMENT ON COLUMN cf_crop_stage_state.stage_source IS
  'Suggested values: prediction, manual.';
COMMENT ON COLUMN cf_calendar_item.status IS
  'Suggested values: active, generated, invalidated.';
COMMENT ON COLUMN cf_calendar_item.parent_task_id IS
  'Upstream business task being continued or revisited by this calendar item, not the direct trigger record owner.';
COMMENT ON COLUMN cf_calendar_item.source_execution_id IS
  'Execution that contains the direct runtime result used to create this calendar item.';
COMMENT ON COLUMN cf_calendar_item.source_execution_record_id IS
  'Direct execution or survey record that triggered this calendar item.';
COMMENT ON COLUMN cf_calendar_item.generation_condition IS
  'Structured calendar generation context such as stage window, algorithm branch, and prerequisite checks.';
COMMENT ON COLUMN cf_task_intent.priority IS
  'Suggested values: low, normal, high, urgent.';
COMMENT ON COLUMN cf_task_intent.status IS
  'Suggested values: pending, in_review, converted, rejected, no_action.';
COMMENT ON COLUMN cf_task_intent.trigger_type IS
  'Suggested values: field_condition, sensor, device, feedback, review, manual, survey_result.';
COMMENT ON COLUMN cf_task_intent.need_more_info_fields IS
  'Structured list of missing fields or evidences required before a decision can be made.';
COMMENT ON COLUMN cf_task_intent.parent_task_id IS
  'Upstream business task being extended, remediated, or reviewed by this task intent.';
COMMENT ON COLUMN cf_task_intent.source_execution_id IS
  'Execution that contains the direct runtime result used to create this task intent.';
COMMENT ON COLUMN cf_task_intent.source_execution_record_id IS
  'Direct execution or survey record that triggered this task intent.';
COMMENT ON COLUMN cf_task_intent.rule_result IS
  'Structured runtime decision result. Suggested keys include algorithmCode, branchType, proposedTask, proposedPlan, and inputRefs.';
COMMENT ON COLUMN cf_review_request.review_type IS
  'Suggested values: task_intent, feedback, execution_exception, plan_change, stage_change.';
COMMENT ON COLUMN cf_review_request.status IS
  'Suggested values: open, in_progress, resolved, cancelled.';
COMMENT ON COLUMN cf_review_request.priority IS
  'Suggested values: low, normal, high, urgent.';
COMMENT ON COLUMN cf_review_request.decision IS
  'Suggested values: approve, reject, need_more_info, no_action, adjust.';
COMMENT ON COLUMN cf_review_request.decision_payload IS
  'Structured review payload. Suggested keys: contextRefs, adjustments, reason.';
COMMENT ON COLUMN cf_farming_task.priority IS
  'Suggested values: low, normal, high, urgent.';
COMMENT ON COLUMN cf_farming_task.status IS
  'Suggested values: pending, ready, running, completed, failed, cancelled.';
COMMENT ON COLUMN cf_farming_task.execution_mode IS
  'Suggested values: manual, device, drone, third_party.';
COMMENT ON COLUMN cf_farming_task.parent_task_id IS
  'Upstream business task being continued or remediated by this formal farming task.';
COMMENT ON COLUMN cf_farming_task.source_execution_id IS
  'Execution that contains the direct runtime result or approved review basis used to generate this farming task.';
COMMENT ON COLUMN cf_farming_task.source_execution_record_id IS
  'Direct execution or survey record that triggered this farming task generation.';
COMMENT ON COLUMN cf_operation_plan.plan_type IS
  'Suggested values align with task categories such as irrigation, fertilization, plant_protection.';
COMMENT ON COLUMN cf_operation_plan.status IS
  'Suggested values: draft, active, superseded, invalidated.';
COMMENT ON COLUMN cf_operation_plan.execution_mode IS
  'Suggested values: manual, device, drone, third_party.';
COMMENT ON COLUMN cf_operation_plan.parameters IS
  'Structured operation parameters such as dosage, water volume, prescriptions, and control targets.';
COMMENT ON COLUMN cf_operation_plan.prescription_map IS
  'Structured prescription map or area-based differentiated parameters.';
COMMENT ON COLUMN cf_operation_plan.acceptance_criteria IS
  'Structured acceptance and verification criteria for execution outcome.';
COMMENT ON COLUMN cf_execution.execution_mode IS
  'Suggested values: manual, device, drone, third_party.';
COMMENT ON COLUMN cf_execution.status IS
  'Suggested values: pending, running, completed, failed, cancelled.';
COMMENT ON COLUMN cf_execution_record.record_type IS
  'Suggested values: status_update, result, manual_upload, device_callback, survey_result.';
COMMENT ON COLUMN cf_execution_record.result_payload IS
  'Structured execution or survey result payload. May become the direct input for follow-up orchestration.';
COMMENT ON COLUMN cf_execution_record.attachments IS
  'Structured attachment metadata such as images, files, or trajectories.';
COMMENT ON COLUMN cf_evaluation.source_type IS
  'Suggested values: system, algorithm, user, external.';
COMMENT ON COLUMN cf_evaluation.result IS
  'Suggested values: pass, warning, fail, unknown.';
COMMENT ON COLUMN cf_evaluation.metrics IS
  'Structured evaluation metrics and indicator values.';
COMMENT ON COLUMN cf_feedback.source_type IS
  'Suggested values: system, algorithm, user, external.';
COMMENT ON COLUMN cf_feedback.feedback_type IS
  'Suggested values: completed, incomplete, abnormal, remedial_needed, adjust_future.';
COMMENT ON COLUMN cf_feedback.severity IS
  'Suggested values: info, warning, critical.';
COMMENT ON COLUMN cf_feedback.status IS
  'Suggested values: open, processing, closed.';
COMMENT ON COLUMN cf_feedback.details IS
  'Structured feedback details, including runtime anomalies or follow-up recommendations.';
COMMENT ON COLUMN cf_system_notification.notification_type IS
  'Suggested values: review_required, task_due, task_updated, execution_alert, info.';
COMMENT ON COLUMN cf_system_notification.status IS
  'Suggested values: unread, read, dismissed.';

CREATE INDEX IF NOT EXISTS idx_cf_farm_field_relation_farm_id
  ON cf_farm_field_relation (farm_id);
CREATE INDEX IF NOT EXISTS idx_cf_farm_field_relation_field_id
  ON cf_farm_field_relation (field_id);
CREATE INDEX IF NOT EXISTS idx_cf_code_dict_category_active
  ON cf_code_dict (category, is_active);
CREATE INDEX IF NOT EXISTS idx_cf_user_status
  ON cf_user (status);
CREATE INDEX IF NOT EXISTS idx_cf_user_account_user_id
  ON cf_user_account (user_id);
CREATE INDEX IF NOT EXISTS idx_cf_user_account_status
  ON cf_user_account (status);
CREATE INDEX IF NOT EXISTS idx_cf_planting_plan_farm_id
  ON cf_planting_plan (farm_id);
CREATE INDEX IF NOT EXISTS idx_cf_planting_plan_variety_id
  ON cf_planting_plan (variety_id);
CREATE INDEX IF NOT EXISTS idx_cf_planting_plan_culti_type_code
  ON cf_planting_plan (culti_type_code);
CREATE INDEX IF NOT EXISTS idx_cf_planting_plan_planting_method_code
  ON cf_planting_plan (planting_method_code);
CREATE INDEX IF NOT EXISTS idx_cf_plan_field_relation_plan_id
  ON cf_planting_plan_field_relation (planting_plan_id);
CREATE INDEX IF NOT EXISTS idx_cf_plan_field_relation_field_id
  ON cf_planting_plan_field_relation (field_id);
CREATE INDEX IF NOT EXISTS idx_cf_event_record_plan_id
  ON cf_event_record (planting_plan_id);
CREATE INDEX IF NOT EXISTS idx_cf_event_record_type_status
  ON cf_event_record (event_type, processing_status);
CREATE INDEX IF NOT EXISTS idx_cf_stage_prediction_snapshot_plan_id
  ON cf_stage_prediction_snapshot (planting_plan_id);
CREATE INDEX IF NOT EXISTS idx_cf_calendar_item_plan_status
  ON cf_calendar_item (planting_plan_id, status);
CREATE INDEX IF NOT EXISTS idx_cf_calendar_item_task_subtype
  ON cf_calendar_item (task_subtype);
CREATE INDEX IF NOT EXISTS idx_cf_calendar_item_parent_task_id
  ON cf_calendar_item (parent_task_id);
CREATE INDEX IF NOT EXISTS idx_cf_calendar_item_source_execution_id
  ON cf_calendar_item (source_execution_id);
CREATE INDEX IF NOT EXISTS idx_cf_calendar_item_source_execution_record_id
  ON cf_calendar_item (source_execution_record_id);
CREATE INDEX IF NOT EXISTS idx_cf_task_intent_plan_status
  ON cf_task_intent (planting_plan_id, status);
CREATE INDEX IF NOT EXISTS idx_cf_task_intent_parent_task_id
  ON cf_task_intent (parent_task_id);
CREATE INDEX IF NOT EXISTS idx_cf_task_intent_source_execution_id
  ON cf_task_intent (source_execution_id);
CREATE INDEX IF NOT EXISTS idx_cf_task_intent_source_execution_record_id
  ON cf_task_intent (source_execution_record_id);
CREATE INDEX IF NOT EXISTS idx_cf_review_request_plan_status
  ON cf_review_request (planting_plan_id, status);
CREATE INDEX IF NOT EXISTS idx_cf_review_request_assigned_user_id
  ON cf_review_request (assigned_user_id);
CREATE INDEX IF NOT EXISTS idx_cf_review_request_source_entity
  ON cf_review_request (source_entity_type, source_entity_id);
CREATE INDEX IF NOT EXISTS idx_cf_farming_task_plan_status
  ON cf_farming_task (planting_plan_id, status);
CREATE INDEX IF NOT EXISTS idx_cf_farming_task_task_subtype
  ON cf_farming_task (task_subtype);
CREATE INDEX IF NOT EXISTS idx_cf_farming_task_review_request_id
  ON cf_farming_task (review_request_id);
CREATE INDEX IF NOT EXISTS idx_cf_farming_task_parent_task_id
  ON cf_farming_task (parent_task_id);
CREATE INDEX IF NOT EXISTS idx_cf_farming_task_source_execution_id
  ON cf_farming_task (source_execution_id);
CREATE INDEX IF NOT EXISTS idx_cf_farming_task_source_execution_record_id
  ON cf_farming_task (source_execution_record_id);
CREATE UNIQUE INDEX IF NOT EXISTS uk_cf_operation_plan_active_task
  ON cf_operation_plan (farming_task_id)
  WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_cf_execution_task_id
  ON cf_execution (farming_task_id);
CREATE INDEX IF NOT EXISTS idx_cf_execution_operation_plan_id
  ON cf_execution (operation_plan_id);
CREATE INDEX IF NOT EXISTS idx_cf_execution_status
  ON cf_execution (status);
CREATE INDEX IF NOT EXISTS idx_cf_execution_record_execution_id
  ON cf_execution_record (execution_id);
CREATE INDEX IF NOT EXISTS idx_cf_evaluation_execution_id
  ON cf_evaluation (execution_id);
CREATE INDEX IF NOT EXISTS idx_cf_feedback_execution_id
  ON cf_feedback (execution_id);
CREATE INDEX IF NOT EXISTS idx_cf_feedback_requires_review
  ON cf_feedback (requires_review);
CREATE INDEX IF NOT EXISTS idx_cf_system_notification_plan_status
  ON cf_system_notification (planting_plan_id, status);

DROP TRIGGER IF EXISTS trg_cf_farm_updated_at ON cf_farm;
CREATE TRIGGER trg_cf_farm_updated_at
BEFORE UPDATE ON cf_farm
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_field_updated_at ON cf_field;
CREATE TRIGGER trg_cf_field_updated_at
BEFORE UPDATE ON cf_field
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_farm_field_relation_updated_at ON cf_farm_field_relation;
CREATE TRIGGER trg_cf_farm_field_relation_updated_at
BEFORE UPDATE ON cf_farm_field_relation
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_code_dict_updated_at ON cf_code_dict;
CREATE TRIGGER trg_cf_code_dict_updated_at
BEFORE UPDATE ON cf_code_dict
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_user_updated_at ON cf_user;
CREATE TRIGGER trg_cf_user_updated_at
BEFORE UPDATE ON cf_user
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_user_account_updated_at ON cf_user_account;
CREATE TRIGGER trg_cf_user_account_updated_at
BEFORE UPDATE ON cf_user_account
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_rice_variety_updated_at ON cf_rice_variety;
CREATE TRIGGER trg_cf_rice_variety_updated_at
BEFORE UPDATE ON cf_rice_variety
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_planting_plan_updated_at ON cf_planting_plan;
CREATE TRIGGER trg_cf_planting_plan_updated_at
BEFORE UPDATE ON cf_planting_plan
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_plan_field_relation_updated_at ON cf_planting_plan_field_relation;
CREATE TRIGGER trg_cf_plan_field_relation_updated_at
BEFORE UPDATE ON cf_planting_plan_field_relation
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_event_record_updated_at ON cf_event_record;
CREATE TRIGGER trg_cf_event_record_updated_at
BEFORE UPDATE ON cf_event_record
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_stage_prediction_snapshot_updated_at ON cf_stage_prediction_snapshot;
CREATE TRIGGER trg_cf_stage_prediction_snapshot_updated_at
BEFORE UPDATE ON cf_stage_prediction_snapshot
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_crop_stage_state_updated_at ON cf_crop_stage_state;
CREATE TRIGGER trg_cf_crop_stage_state_updated_at
BEFORE UPDATE ON cf_crop_stage_state
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_crop_thermal_time_state_updated_at ON cf_crop_thermal_time_state;
CREATE TRIGGER trg_cf_crop_thermal_time_state_updated_at
BEFORE UPDATE ON cf_crop_thermal_time_state
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_calendar_item_updated_at ON cf_calendar_item;
CREATE TRIGGER trg_cf_calendar_item_updated_at
BEFORE UPDATE ON cf_calendar_item
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_task_intent_updated_at ON cf_task_intent;
CREATE TRIGGER trg_cf_task_intent_updated_at
BEFORE UPDATE ON cf_task_intent
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_review_request_updated_at ON cf_review_request;
CREATE TRIGGER trg_cf_review_request_updated_at
BEFORE UPDATE ON cf_review_request
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_farming_task_updated_at ON cf_farming_task;
CREATE TRIGGER trg_cf_farming_task_updated_at
BEFORE UPDATE ON cf_farming_task
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_operation_plan_updated_at ON cf_operation_plan;
CREATE TRIGGER trg_cf_operation_plan_updated_at
BEFORE UPDATE ON cf_operation_plan
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_execution_updated_at ON cf_execution;
CREATE TRIGGER trg_cf_execution_updated_at
BEFORE UPDATE ON cf_execution
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_execution_record_updated_at ON cf_execution_record;
CREATE TRIGGER trg_cf_execution_record_updated_at
BEFORE UPDATE ON cf_execution_record
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_evaluation_updated_at ON cf_evaluation;
CREATE TRIGGER trg_cf_evaluation_updated_at
BEFORE UPDATE ON cf_evaluation
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_feedback_updated_at ON cf_feedback;
CREATE TRIGGER trg_cf_feedback_updated_at
BEFORE UPDATE ON cf_feedback
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

DROP TRIGGER IF EXISTS trg_cf_system_notification_updated_at ON cf_system_notification;
CREATE TRIGGER trg_cf_system_notification_updated_at
BEFORE UPDATE ON cf_system_notification
FOR EACH ROW
EXECUTE FUNCTION cf_set_updated_at();

-- Expected task_subtype values for the current weed-protection loop include:
--   WF_SOIL_SEAL_WEED
--   WF_STEM_LEAF_WEED_SURVEY
--   WF_STEM_LEAF_WEED
--   WF_STEM_LEAF_WEED_POST_SURVEY
--   WF_STEM_LEAF_WEED_ADDITIONAL_CONTROL
--   WF_PLANT_PROTECTION_SERVICE_EVALUATION
--   WF_PLANT_PROTECTION_SERVICE_EFFECT_SURVEY
