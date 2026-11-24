// Orthographic review renderer with per-pixel depth for nested CAD parts.
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>
#include <vector>
using Vec = std::array<double,3>;
Vec sub(Vec a,Vec b){return {a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
double dot(Vec a,Vec b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
Vec cross(Vec a,Vec b){return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
Vec unit(Vec a){double d=std::sqrt(dot(a,a));return d>0?Vec{a[0]/d,a[1]/d,a[2]/d}:Vec{0,0,0};}
double edge(Vec a,Vec b,double x,double y){return (x-a[0])*(b[1]-a[1])-(y-a[1])*(b[0]-a[0]);}
int main() {
  int width,height;
  double pixelsPerMm;
  Vec eye,center;
  std::cin>>width>>height>>pixelsPerMm>>eye[0]>>eye[1]>>eye[2]>>center[0]>>center[1]>>center[2];
  const Vec forward=unit(eye),right=unit(cross(Vec{0,0,1},forward)),up=cross(forward,right);
  const Vec light=unit(Vec{-.4,-.8,1.0});
  std::vector<double> depth(width*height,-std::numeric_limits<double>::infinity());
  std::vector<unsigned char> pixels(width*height*3);
  for(int i=0;i<width*height;i++) {
    pixels[i*3]=234;
    pixels[i*3+1]=239;
    pixels[i*3+2]=235;
  }
  int meshCount;
  std::cin>>meshCount;
  for(int model=0;model<meshCount;model++) {
    Vec color,offset;
    std::string path;
    std::cin>>color[0]>>color[1]>>color[2]>>offset[0]>>offset[1]>>offset[2];
    std::getline(std::cin>>std::ws,path);
    std::ifstream input(path,std::ios::binary);
    if(!input) return 2;
    std::array<float,18> face;
    while(input.read(reinterpret_cast<char*>(face.data()),sizeof(face))) {
      Vec tri[3];
      for(int i=0;i<3;i++) {
        Vec point={face[i*6]+offset[0],face[i*6+1]+offset[1],face[i*6+2]+offset[2]};
        point=sub(point,center);
        tri[i]={width*.5+pixelsPerMm*dot(point,right),height*.5-pixelsPerMm*dot(point,up),dot(point,forward)};
      }
      double area=edge(tri[0],tri[1],tri[2][0],tri[2][1]);
      if(std::abs(area)<1e-8) continue;
      int x0=std::max(0,int(std::floor(std::min({tri[0][0],tri[1][0],tri[2][0]}))));
      int x1=std::min(width-1,int(std::ceil(std::max({tri[0][0],tri[1][0],tri[2][0]}))));
      int y0=std::max(0,int(std::floor(std::min({tri[0][1],tri[1][1],tri[2][1]}))));
      int y1=std::min(height-1,int(std::ceil(std::max({tri[0][1],tri[1][1],tri[2][1]}))));
      for(int y=y0;y<=y1;y++) for(int x=x0;x<=x1;x++) {
        double u=edge(tri[1],tri[2],x+.5,y+.5)/area;
        double v=edge(tri[2],tri[0],x+.5,y+.5)/area,w=1-u-v;
        if(u<0||v<0||w<0) continue;
        double z=tri[0][2]*u+tri[1][2]*v+tri[2][2]*w;
        int index=y*width+x;
        if(z<=depth[index]) continue;
        depth[index]=z;
        Vec normal=unit(Vec{
          u*face[3]+v*face[9]+w*face[15],
          u*face[4]+v*face[10]+w*face[16],
          u*face[5]+v*face[11]+w*face[17]
        });
        double lighting=.44+.51*std::max(0.0,dot(normal,light))
                          +.12*std::max(0.0,dot(normal,forward));
        for(int channel=0;channel<3;channel++)
          pixels[index*3+channel]=static_cast<unsigned char>(std::clamp(color[channel]*lighting*255,0.,255.));
      }
    }
  }
  std::cout<<"P6\n"<<width<<" "<<height<<"\n255\n";
  std::cout.write(reinterpret_cast<char*>(pixels.data()),pixels.size());
}
