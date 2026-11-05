// SPDX-License-Identifier: GPL-2.0
/* Appended to extracted real code by test_atomics.py. No hardware/SMP claim. */
static uint64_t random_state = 0x515babe;
static uint64_t rnd(void)
{
 random_state ^= random_state << 13; random_state ^= random_state >> 7;
 random_state ^= random_state << 17; return random_state;
}
static void execute(u32 *image, int count, uint64_t *r, uint64_t *mem,
                    uint64_t address, int failures, bool interfere, bool ordered)
{
 int pc=0,steps=0,barriers=0;
 while(pc<count) {
  assert(pc>=0 && ++steps<150);
  u32 w=image[pc]; unsigned rd=w&31,rn=(w>>5)&31,rm=(w>>16)&31;
  bool wide=w>>31; uint64_t mask=wide?UINT64_MAX:UINT32_MAX, value=0;
  u32 base=w&0x7f800000;
  if(base==0x52800000 || base==0x12800000 || base==0x72800000) {
   unsigned shift=((w>>21)&3)*16; uint64_t imm=((w>>5)&65535ULL)<<shift;
   if(base==0x52800000) value=imm;
   else if(base==0x12800000) value=~imm;
   else value=(r[rd]&~(65535ULL<<shift))|imm;
   r[rd]=value&mask;
  } else if((w&0x7f000000)==0x11000000) {
   r[rd]=(r[rn]+((w>>10)&4095))&mask;
  } else if((w&0x7f200000)==0x0b000000) {
   r[rd]=(r[rn]+r[rm])&mask;
  } else if((w&0x7f200000)==0x0a000000 || (w&0x7f200000)==0x2a000000 || (w&0x7f200000)==0x4a000000) {
   unsigned op=(w>>29)&3;
   value=op==0?(r[rn]&r[rm]):op==1?(r[rn]|r[rm]):(r[rn]^r[rm]);
   r[rd]=value&mask;
  } else if((w&0x3f400000)==0x08400000) {
   assert(r[rn]==address); mask=(w&(1U<<30))?UINT64_MAX:UINT32_MAX;
   r[rd]=*mem&mask;
  } else if((w&0x3f400000)==0x08000000) {
   unsigned status=(w>>16)&31; mask=(w&(1U<<30))?UINT64_MAX:UINT32_MAX;
   assert(r[rn]==address);
   if(failures) {
    failures--; r[status]=1;
    if(interfere) { *mem ^= 0x80; interfere=false; }
   } else { *mem=(*mem&~mask)|(r[rd]&mask); r[status]=0; }
  } else if((w&0x3f20fc00)==0x38200000) {
   mask=(w&(1U<<30))?UINT64_MAX:UINT32_MAX;
   assert(r[rn]==address && rd==31);
   *mem=(*mem&~mask)|((*mem+r[rm])&mask);
  } else if((w&0x7f000000)==0x35000000) {
   int offset=(w>>5)&0x7ffff;
   if(offset&(1<<18)) offset-=1<<19;
   if(r[rd]&mask) { pc+=offset; continue; }
  } else if(w==0xd5033bbf) { barriers++;
  } else { fprintf(stderr,"unknown %08x at %d\n",w,pc); assert(0); }
  pc++;
 }
 assert(!ordered || barriers==1);
}
int main(void)
{
 const int operations[]={BPF_ADD,BPF_AND,BPF_OR,BPF_XOR,BPF_ADD|BPF_FETCH,
  BPF_AND|BPF_FETCH,BPF_OR|BPF_FETCH,BPF_XOR|BPF_FETCH,BPF_XCHG,BPF_CMPXCHG};
 const int offsets[]={0,8,-8,32760,-32768};
 unsigned long checks=0;
 for(int wide=0;wide<2;wide++) for(int cap=0;cap<2;cap++) for(int op=0;op<10;op++) {
  for(int sample=0;sample<5000;sample++) {
   u32 image[100]={0}; struct jit_ctx ctx={.image=image},dry={0};
   unsigned dst=rnd()%11,src=rnd()%10;
   struct bpf_insn insn={.code=BPF_STX|BPF_ATOMIC|(wide?BPF_DW:BPF_W),.dst_reg=dst,.src_reg=src,
    .imm=operations[op],.off=offsets[sample%5]};
   uint64_t r[32],expected[32];
   for(int i=0;i<32;i++) r[i]=rnd();
   r[bpf2a64[dst]]=0x100000;
   memcpy(expected,r,sizeof(r));
   uint64_t mask=wide?UINT64_MAX:UINT32_MAX;
   uint64_t operand=r[bpf2a64[src]]&mask, compare=r[bpf2a64[0]]&mask;
   uint64_t memory=(op==9 && sample%2)?compare:rnd(),before=memory;
   int failures=sample%3; bool change=sample%4==0;
   uint64_t old=memory&mask;
   bool lse_path=cap && op==0;
   if(!lse_path && failures && change && (op!=9 || old==compare)) memory ^= 0x80;
   old=memory&mask;
   uint64_t result;
   switch(operations[op]&~BPF_FETCH) {
    case BPF_ADD:result=old+operand;break;
    case BPF_AND:result=old&operand;break;
    case BPF_OR:result=old|operand;break;
    case BPF_XOR:result=old^operand;break;
    default:result=operand;break;
   }
   if(op!=9 || old==compare) memory=(memory&~mask)|(result&mask);
   if(op==9) expected[bpf2a64[0]]=old;
   else if(operations[op]&BPF_FETCH) expected[bpf2a64[src]]=old;
   uint64_t expected_memory=memory; memory=before;
   lse=cap;
   assert(build_atomic(&insn,&dry)==0 && build_atomic(&insn,&ctx)==0);
   assert(dry.idx==ctx.idx && ctx.idx<100);
   execute(image,ctx.idx,r,&memory,0x100000+(int64_t)insn.off,failures,change,op>=4);
   assert(memory==expected_memory);
   for(int i=0;i<11;i++) assert(r[bpf2a64[i]]==expected[bpf2a64[i]]);
   checks++;
  }
 }
 printf("PASS: %lu real ARM64 atomic code cases, widths/LSE/aliases/offsets/exclusive retries/interference/barrier paths\n",checks);
 return 0;
}
