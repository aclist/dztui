#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define R 6371
#define TO_RAD (3.1415926536 / 180)
double dist(double th1, double ph1, double th2, double ph2)
{
	double dx, dy, dz;
	ph1 -= ph2;
	ph1 *= TO_RAD, th1 *= TO_RAD, th2 *= TO_RAD;

	dz = sin(th1) - sin(th2);
	dx = cos(ph1) * cos(th1) - cos(th2);
	dy = sin(ph1) * cos(th1);
	return asin(sqrt(dx * dx + dy * dy + dz * dz) / 2) * 2 * R;
}

int main(int argc, const char * argv[])
{
	if(argc < 5 || argc > 5){
		return 1;
	}
	float coords[4];
	for(int i=1;i<5;i++){
		if(atof(argv[i]) == 0){
			return 1;
		}
		coords[i] = atof(argv[i]);
	}
	
	float coord1 = atof(argv[1]);
	float coord2 = atof(argv[2]);
	float coord3 = atof(argv[3]);
	float coord4 = atof(argv[4]);

	double d = dist(coords[1], coords[2], coords[3], coords[4]);
	printf("%.1f\n", d);

	return 0;
}
