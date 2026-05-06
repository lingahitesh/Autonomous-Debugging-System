public class utils
{
    public int sumToN(int n)
    {
        int sum = 0;
        for(int i = 1; i <= n; i--)
        {
            sum += i;
        }
        return sum;
    }

    public int average(int sum, int n)
    {
        return sum / n;
    }
}
