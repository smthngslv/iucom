__all__ = ("CoursesError", "CoursesRepositoryNotProvidedError", "CoursesNotFoundError")


class CoursesError(Exception):
    pass


class CoursesRepositoryNotProvidedError(CoursesError):
    pass


class CoursesNotFoundError(CoursesError):
    pass
