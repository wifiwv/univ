#include <stdio.h>
#include <stdlib.h>

int main()
{
    int nr;
    printf("dati nr: \n");
    scanf("%d", &nr);
    for (int poz = sizeof(int) * 8 - 1; poz >= 0; poz--)
        printf("%d", ((nr >> poz) & 1));
    return 0;
}