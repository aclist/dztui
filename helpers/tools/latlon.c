// This small program computes the distance between two points on the Earths
// surface. The algorithm used for computing is called haversine formula.
// Source for the algorithm can be found here:
// https://en.wikipedia.org/wiki/Haversine_formula

#include <math.h>
#include <stdlib.h>
#include <stdio.h>

// Earth's radius in meters. To pretty-print the result for the end-user, it is
// recommended to divide the result by 1,000 and round it.
#define RADIUS ((12756L / 2.0L) * 1000L)

// PI natural constant
#define PI 3.1415926536L

// coordinates struct for storing points
struct Coordinate {
    double latitude;
    double longitude;
};

/**
 * @brief Calculates a radian value from an angle
 */
double radian_from(const double angle) {
    return (angle * PI) / 180;
}

/**
 * @brief Calculate the haversine function from an angle in radian
 */
double haversine(const double angle) { return ((1.0L - cos(angle)) / 2); }

/**
 * @brief Calculate the distance between two coordinates
 */
double great_circle_distance(const struct Coordinate a,
                             const struct Coordinate b) {

    // calculate longitude and latitude differences
    struct Coordinate diff_coord = {
        .longitude = a.longitude - b.longitude,
        .latitude  = a.latitude - b.latitude,
    };

    // calculate haversine(theta) value, where theta is the angle between the
    // two coordinates
    double hav_theta = haversine(diff_coord.latitude)
                       + cos(a.latitude) * cos(b.latitude) * haversine(diff_coord.longitude);

    // calculate distance from radius, and haversine(theta) values 
    double distance = 2 * RADIUS * asin(sqrt(hav_theta));

    return distance;
}

int main(int argc, const char* argv[]) {
    if (argc < 5 || argc > 5) {
        return 1;
    }

    const struct Coordinate a = {
        .latitude  = radian_from(atof(argv[1])),
        .longitude = radian_from(atof(argv[2])),
    };
    const struct Coordinate b = {
        .latitude  = radian_from(atof(argv[3])),
        .longitude = radian_from(atof(argv[4])),
    };

    printf("%.1f\n", great_circle_distance(a, b));

    return 0;
}
