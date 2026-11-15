// SPDX-License-Identifier: GPL-2.0

#include <linux/buildid.h>
#include <linux/elf.h>
#include <linux/pagemap.h>

#define BUILD_ID 3
/*
 * Parse build id from the note segment. This logic can be shared between
 * 32-bit and 64-bit system, because Elf32_Nhdr and Elf64_Nhdr are
 * identical.
 */
static inline int parse_build_id(void *page_addr, unsigned char *build_id,
				__u32 *size, void *note_start,
				Elf32_Word note_size)
{
	unsigned long base = (unsigned long)page_addr;
	unsigned long start = (unsigned long)note_start;
	size_t off = 0;

	if (start < base || start - base > PAGE_SIZE ||
	    note_size > PAGE_SIZE - (start - base))
		return -EINVAL;
	while (note_size - off >= sizeof(Elf32_Nhdr)) {
		Elf32_Nhdr hdr;
		u64 names, descs;
		size_t remain = note_size - off - sizeof(hdr);
		const char *name = note_start + off + sizeof(hdr);

		/* ELF note/program headers need not be naturally aligned. */
		memcpy(&hdr, note_start + off, sizeof(hdr));
		names = ((u64)hdr.n_namesz + 3) & ~3ULL;
		descs = ((u64)hdr.n_descsz + 3) & ~3ULL;
		if (names > remain || descs > remain - names)
			return -EINVAL;
		if (hdr.n_type == BUILD_ID && hdr.n_namesz == sizeof("GNU") &&
		    hdr.n_descsz && hdr.n_descsz <= BUILD_ID_SIZE_MAX &&
		    !memcmp(name, "GNU", sizeof("GNU"))) {
			memcpy(build_id, name + names, hdr.n_descsz);
			memset(build_id + hdr.n_descsz, 0,
			       BUILD_ID_SIZE_MAX - hdr.n_descsz);
			if (size)
				*size = hdr.n_descsz;
			return 0;
		}
		off += sizeof(hdr) + names + descs;
	}
	return -EINVAL;
}

static int get_build_id_32(void *page_addr, unsigned char *build_id,
			   __u32 *size)
{
	Elf32_Ehdr hdr;
	unsigned int i;

	memcpy(&hdr, page_addr, sizeof(hdr));
	if (hdr.e_ehsize != sizeof(hdr) ||
	    hdr.e_phentsize != sizeof(Elf32_Phdr) ||
	    hdr.e_phoff < sizeof(hdr) || hdr.e_phoff > PAGE_SIZE ||
	    hdr.e_phnum > (PAGE_SIZE - hdr.e_phoff) / sizeof(Elf32_Phdr))
		return -EINVAL;
	for (i = 0; i < hdr.e_phnum; i++) {
		Elf32_Phdr phdr;

		memcpy(&phdr, page_addr + hdr.e_phoff + i * sizeof(phdr),
		       sizeof(phdr));
		if (phdr.p_type != PT_NOTE || phdr.p_offset > PAGE_SIZE ||
		    phdr.p_filesz > PAGE_SIZE - phdr.p_offset)
			continue;
		if (!parse_build_id(page_addr, build_id, size,
				    page_addr + phdr.p_offset, phdr.p_filesz))
			return 0;
	}
	return -EINVAL;
}

static int get_build_id_64(void *page_addr, unsigned char *build_id,
			   __u32 *size)
{
	Elf64_Ehdr hdr;
	unsigned int i;

	memcpy(&hdr, page_addr, sizeof(hdr));
	if (hdr.e_ehsize != sizeof(hdr) ||
	    hdr.e_phentsize != sizeof(Elf64_Phdr) ||
	    hdr.e_phoff < sizeof(hdr) || hdr.e_phoff > PAGE_SIZE ||
	    hdr.e_phnum > (PAGE_SIZE - hdr.e_phoff) / sizeof(Elf64_Phdr))
		return -EINVAL;
	for (i = 0; i < hdr.e_phnum; i++) {
		Elf64_Phdr phdr;

		memcpy(&phdr, page_addr + hdr.e_phoff + i * sizeof(phdr),
		       sizeof(phdr));
		if (phdr.p_type != PT_NOTE || phdr.p_offset > PAGE_SIZE ||
		    phdr.p_filesz > PAGE_SIZE - phdr.p_offset)
			continue;
		if (!parse_build_id(page_addr, build_id, size,
				    page_addr + phdr.p_offset, phdr.p_filesz))
			return 0;
	}
	return -EINVAL;
}

/*
 * Parse build ID of ELF file mapped to vma
 * @vma:      vma object
 * @build_id: buffer to store build id, at least BUILD_ID_SIZE long
 * @size:     returns actual build id size in case of success
 *
 * Returns 0 on success, otherwise error (< 0).
 */
int build_id_parse(struct vm_area_struct *vma, unsigned char *build_id,
		   __u32 *size)
{
	Elf32_Ehdr *ehdr;
	struct page *page;
	void *page_addr;
	int ret;

	/* only works for page backed storage  */
	if (!vma->vm_file)
		return -EINVAL;

	page = find_get_page(vma->vm_file->f_mapping, 0);
	if (!page)
		return -EFAULT;	/* page not mapped */

	ret = -EINVAL;
	page_addr = kmap_atomic(page);
	ehdr = (Elf32_Ehdr *)page_addr;

	/* compare magic x7f "ELF" */
	if (memcmp(ehdr->e_ident, ELFMAG, SELFMAG) != 0)
		goto out;

#ifdef __BIG_ENDIAN_BITFIELD
	if (ehdr->e_ident[EI_DATA] != ELFDATA2MSB)
#else
	if (ehdr->e_ident[EI_DATA] != ELFDATA2LSB)
#endif
		goto out;
	if (ehdr->e_ident[EI_VERSION] != EV_CURRENT)
		goto out;

	/* only support executable file and shared object file */
	if (ehdr->e_type != ET_EXEC && ehdr->e_type != ET_DYN)
		goto out;

	if (ehdr->e_ident[EI_CLASS] == ELFCLASS32)
		ret = get_build_id_32(page_addr, build_id, size);
	else if (ehdr->e_ident[EI_CLASS] == ELFCLASS64)
		ret = get_build_id_64(page_addr, build_id, size);
out:
	kunmap_atomic(page_addr);
	put_page(page);
	return ret;
}
