def engineer_can_do_job(engineer, job):
    if job.required_skill not in engineer.skills:
        return False
    if job.required_vehicle_type and engineer.vehicle_type != job.required_vehicle_type:
        return False
    return True
