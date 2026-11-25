import rerun as rr

rr.init("get_started4", spawn=True)
rr.log("world/car", rr.Boxes3D(half_sizes=[1, 1, 1], colors=[255, 0, 0]))
for i in range(1, 100):
    rr.set_time("log_time", timestamp=i/100)

    rr.log("world/car", rr.Transform3D(translation=[i/100, 0, 0]))



