from app.bootstrap import seed_reference_data
from app.db.session import get_session_factory


def main() -> None:
    session_factory = get_session_factory()
    with session_factory() as session:
        summary = seed_reference_data(session)
        session.commit()

    print("Reference seed completed.")
    print(f"code_dict_count={summary.code_dict_count}")
    print(f"crop_stage_dict_count={summary.crop_stage_dict_count}")
    print(f"rice_variety_count={summary.rice_variety_count}")
    print(f"rice_control_window_level1_count={summary.rice_control_window_level1_count}")
    print(f"farm_id={summary.farm_id}")
    print(f"field_ids={summary.field_ids}")
    print(f"farm_field_relation_count={summary.farm_field_relation_count}")


if __name__ == "__main__":
    main()
