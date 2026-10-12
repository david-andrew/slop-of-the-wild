/* Conservative two-sided body depth at sample centres. Equipment is separate.
 * Input x/y are viewport pixels, w is positive camera-space depth. */
#include <math.h>
#include <stdint.h>

void framing_raster(const double *points, const int64_t *indices, int count,
                    double *depth, int width, int height) {
    for (int t = 0; t < count; ++t) {
        const double *a = points + indices[t * 3] * 3;
        const double *b = points + indices[t * 3 + 1] * 3;
        const double *c = points + indices[t * 3 + 2] * 3;
        if (a[2] <= .1 || b[2] <= .1 || c[2] <= .1) continue;
        double det = (b[1]-c[1])*(a[0]-c[0]) + (c[0]-b[0])*(a[1]-c[1]);
        if (fabs(det) < 1e-10) continue;
        int x0 = (int)fmax(0, floor(fmin(a[0],fmin(b[0],c[0]))));
        int x1 = (int)fmin(width-1, ceil(fmax(a[0],fmax(b[0],c[0]))));
        int y0 = (int)fmax(0, floor(fmin(a[1],fmin(b[1],c[1]))));
        int y1 = (int)fmin(height-1, ceil(fmax(a[1],fmax(b[1],c[1]))));
        for (int y = y0; y <= y1; ++y) for (int x = x0; x <= x1; ++x) {
            double u = ((b[1]-c[1])*(x+.5-c[0]) + (c[0]-b[0])*(y+.5-c[1]))/det;
            double v = ((c[1]-a[1])*(x+.5-c[0]) + (a[0]-c[0])*(y+.5-c[1]))/det;
            double w = 1-u-v;
            if (u < -1e-9 || v < -1e-9 || w < -1e-9) continue;
            double z = 1/(u/a[2] + v/b[2] + w/c[2]);
            int at = y*width+x;
            if (z < depth[at]) depth[at] = z;
        }
    }
}

/* Exact surface separation of the posed triangle sets, accelerated by AABBs. */
#include <stdlib.h>
#include <float.h>
typedef struct { double x,y,z; } V;
static V sub(V a,V b){return (V){a.x-b.x,a.y-b.y,a.z-b.z};}
static V add(V a,V b){return (V){a.x+b.x,a.y+b.y,a.z+b.z};}
static V mul(V a,double t){return (V){a.x*t,a.y*t,a.z*t};}
static double dot(V a,V b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static V cross(V a,V b){return (V){a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
static double clamp01(double x){return fmax(0,fmin(1,x));}
static double point_tri(V p,V a,V b,V c){
    V ab=sub(b,a),ac=sub(c,a),ap=sub(p,a);double d1=dot(ab,ap),d2=dot(ac,ap);
    if(d1<=0&&d2<=0)return dot(ap,ap);
    V bp=sub(p,b);double d3=dot(ab,bp),d4=dot(ac,bp);
    if(d3>=0&&d4<=d3)return dot(bp,bp);
    double vc=d1*d4-d3*d2;
    if(vc<=0&&d1>=0&&d3<=0){V q=sub(p,add(a,mul(ab,d1/(d1-d3))));return dot(q,q);}
    V cp=sub(p,c);double d5=dot(ab,cp),d6=dot(ac,cp);
    if(d6>=0&&d5<=d6)return dot(cp,cp);
    double vb=d5*d2-d1*d6;
    if(vb<=0&&d2>=0&&d6<=0){V q=sub(p,add(a,mul(ac,d2/(d2-d6))));return dot(q,q);}
    double va=d3*d6-d5*d4;
    if(va<=0&&(d4-d3)>=0&&(d5-d6)>=0){V q=sub(p,add(b,mul(sub(c,b),(d4-d3)/((d4-d3)+(d5-d6)))));return dot(q,q);}
    double den=va+vb+vc;
    if(fabs(den)<1e-24)return fmin(dot(ap,ap),fmin(dot(bp,bp),dot(cp,cp)));
    V q=sub(p,add(a,add(mul(ab,vb/den),mul(ac,vc/den))));return dot(q,q);
}
static double segments(V p,V q,V a,V b){
    V u=sub(q,p),v=sub(b,a),r=sub(p,a);double aa=dot(u,u),bb=dot(v,v),f=dot(v,r),s,t;
    if(aa<1e-20&&bb<1e-20)return dot(r,r);
    if(aa<1e-20){s=0;t=clamp01(f/bb);}
    else{double c=dot(u,r);if(bb<1e-20){t=0;s=clamp01(-c/aa);}
        else{double e=dot(u,v),den=aa*bb-e*e;s=den>1e-20?clamp01((e*f-c*bb)/den):0;t=(e*s+f)/bb;
            if(t<0){t=0;s=clamp01(-c/aa);}else if(t>1){t=1;s=clamp01((e-c)/aa);}}}
    V d=sub(add(p,mul(u,s)),add(a,mul(v,t)));return dot(d,d);
}
static int segment_tri(V p,V q,V a,V b,V c){
    V d=sub(q,p),ab=sub(b,a),ac=sub(c,a),h=cross(d,ac);double det=dot(ab,h);
    if(fabs(det)<1e-12)return 0;
    V s=sub(p,a);double u=dot(s,h)/det;if(u<-1e-9||u>1+1e-9)return 0;
    V t=cross(s,ab);double v=dot(d,t)/det;if(v<-1e-9||u+v>1+1e-9)return 0;
    double along=dot(ac,t)/det;return along>=-1e-9&&along<=1+1e-9;
}
typedef struct {V p[3];double lo[3],hi[3],centre[3];} Tri;
typedef struct {double lo[3],hi[3];int begin,end,left,right;} Node;
typedef struct {Tri *tris;Node *nodes;int used;} Tree;
static int sort_axis;
static int tri_compare(const void *a,const void *b){double d=((const Tri*)a)->centre[sort_axis]-((const Tri*)b)->centre[sort_axis];return d<0?-1:d>0;}
static int build_tree(Tree *tree,int begin,int end){
    int id=tree->used++;Node *n=&tree->nodes[id];n->begin=begin;n->end=end;n->left=n->right=-1;
    for(int k=0;k<3;k++){n->lo[k]=DBL_MAX;n->hi[k]=-DBL_MAX;for(int j=begin;j<end;j++){n->lo[k]=fmin(n->lo[k],tree->tris[j].lo[k]);n->hi[k]=fmax(n->hi[k],tree->tris[j].hi[k]);}}
    if(end-begin<=8)return id;
    sort_axis=0;for(int k=1;k<3;k++)if(n->hi[k]-n->lo[k]>n->hi[sort_axis]-n->lo[sort_axis])sort_axis=k;
    qsort(tree->tris+begin,end-begin,sizeof(Tri),tri_compare);
    int mid=(begin+end)/2;n->left=build_tree(tree,begin,mid);n->right=build_tree(tree,mid,end);return id;
}
static Tree make_tree(const double *p,const int64_t *idx,int count){
    Tree tree={malloc(sizeof(Tri)*count),malloc(sizeof(Node)*(count*2+1)),0};
    if(!tree.tris||!tree.nodes){free(tree.tris);free(tree.nodes);return (Tree){0};}
    for(int j=0;j<count;j++){Tri *t=&tree.tris[j];for(int v=0;v<3;v++){const double *q=p+idx[j*3+v]*3;t->p[v]=(V){q[0],q[1],q[2]};}
        for(int k=0;k<3;k++){t->lo[k]=DBL_MAX;t->hi[k]=-DBL_MAX;t->centre[k]=0;for(int v=0;v<3;v++){double x=p[idx[j*3+v]*3+k];t->lo[k]=fmin(t->lo[k],x);t->hi[k]=fmax(t->hi[k],x);t->centre[k]+=x/3;}}}
    build_tree(&tree,0,count);return tree;
}
static double box_distance(const double *al,const double *ah,const double *bl,const double *bh){double d=0;for(int k=0;k<3;k++){double x=fmax(0,fmax(al[k]-bh[k],bl[k]-ah[k]));d+=x*x;}return d;}
static double tri_distance(const Tri *a,const Tri *b){
    double best=DBL_MAX;
    for(int i=0;i<3;i++){if(segment_tri(a->p[i],a->p[(i+1)%3],b->p[0],b->p[1],b->p[2])||segment_tri(b->p[i],b->p[(i+1)%3],a->p[0],a->p[1],a->p[2]))return 0;
        best=fmin(best,point_tri(a->p[i],b->p[0],b->p[1],b->p[2]));best=fmin(best,point_tri(b->p[i],a->p[0],a->p[1],a->p[2]));
        for(int j=0;j<3;j++)best=fmin(best,segments(a->p[i],a->p[(i+1)%3],b->p[j],b->p[(j+1)%3]));}return best;
}
static void tree_distance(Tree *a,int ai,Tree *b,int bi,double *best){
    Node *x=&a->nodes[ai],*y=&b->nodes[bi];if(*best<=1e-16||box_distance(x->lo,x->hi,y->lo,y->hi)>=*best)return;
    if(x->left<0&&y->left<0){for(int i=x->begin;i<x->end;i++)for(int j=y->begin;j<y->end;j++){Tri *at=&a->tris[i],*bt=&b->tris[j];if(box_distance(at->lo,at->hi,bt->lo,bt->hi)<*best)*best=fmin(*best,tri_distance(at,bt));}return;}
    if(y->left<0||(x->left>=0&&x->end-x->begin>y->end-y->begin)){tree_distance(a,x->left,b,bi,best);tree_distance(a,x->right,b,bi,best);}
    else{tree_distance(a,ai,b,y->left,best);tree_distance(a,ai,b,y->right,best);}
}
double framing_mesh_gap(const double *a,const int64_t *ia,int na,const double *b,const int64_t *ib,int nb){
    if(na<=0||nb<=0)return DBL_MAX;
    Tree at=make_tree(a,ia,na),bt=make_tree(b,ib,nb);double best=DBL_MAX;
    if(!at.tris||!bt.tris)best=NAN;else tree_distance(&at,0,&bt,0,&best);
    free(at.tris);free(at.nodes);free(bt.tris);free(bt.nodes);return sqrt(best);
}
