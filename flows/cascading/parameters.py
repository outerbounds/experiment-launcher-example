from metaflow import Parameter

class Parameters():

    animal1 = Parameter("animal1",
                       required=True,
                       default=None,
                       help="Specify the first animal")

    animal2 = Parameter("animal2",
                       required=True,
                       default=None,
                       help="Specify the second animal")

    count = Parameter("count",
                      type=int,
                      help="Number of animals",
                      default=0)

    ratio = Parameter("ratio",
                      help="Ratio between the animals (0.0-1.0)",
                      type=float)
